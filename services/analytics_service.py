"""Behavioural instrumentation.

The point of this layer is to answer questions the code cannot: how many people
finish onboarding, how many reminders turn into check-ins, how often the
guidance offer is accepted, what a user costs in Anthropic calls. None of that
is reconstructable later, which is why the event set below is deliberately
broader than what is being asked of it today. Expect to delete some of it.

**Two rules hold this layer in place.**

*Events never carry entry text.* The journal entry is the most sensitive thing
the bot stores; it already lives in the entries collection and goes to Anthropic,
both of which the privacy notice discloses. Copying it into a third store would
create a PII surface nobody disclosed and `/delete` would have to chase. Props
are scalars — scores, counts, lengths, closed-vocabulary labels — and
`_scrub` drops anything long enough to be prose, so a future call site that
passes the wrong variable loses the event rather than leaking the entry.

*Tracking never raises.* A failed insert must not cost a user their check-in.
Every path here is wrapped and logged. This is the opposite of the crisis
lexicon's fail-closed rule, and for the opposite reason: a missing analytics row
harms nobody, while a lost check-in harms the person who wrote it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from repositories.event_repo import EventRepository

logger = logging.getLogger(__name__)

# --- Event taxonomy --------------------------------------------------------
# Onboarding and cohort
ONBOARDING_STARTED = 'onboarding_started'
ONBOARDING_COMPLETED = 'onboarding_completed'
COHORT_RECORDED = 'cohort_recorded'

# The core loop
CHECK_IN_STARTED = 'check_in_started'
CHECK_IN_COMPLETED = 'check_in_completed'
CHECK_IN_FAILED = 'check_in_failed'

# Safety
CRISIS_RESOURCES_SHOWN = 'crisis_resources_shown'
GUIDANCE_OFFERED = 'guidance_offered'
GUIDANCE_ACCEPTED = 'guidance_accepted'
GUIDANCE_DECLINED = 'guidance_declined'

# Scheduled delivery
REMINDER_SENT = 'reminder_sent'
WEEKLY_SUMMARY_SENT = 'weekly_summary_sent'
WEEKLY_SUMMARY_SKIPPED = 'weekly_summary_skipped'

# Read surfaces
HISTORY_VIEWED = 'history_viewed'
STATS_VIEWED = 'stats_viewed'
WEEKLY_SUMMARY_VIEWED = 'weekly_summary_viewed'

# Spend and failure
LLM_BUDGET_EXCEEDED = 'llm_budget_exceeded'
HANDLER_ERROR = 'handler_error'

# A string prop longer than this is prose, not a label, and prose here is a
# leak. The cap is well above every legitimate value the call sites pass
# (category names, menu labels, ISO dates) and well below a journal entry.
_MAX_PROP_CHARS = 64


class AnalyticsService:
    def __init__(self):
        self._repo = EventRepository()

    def track(self, event: str, telegram_id: int | None = None, **props) -> None:
        """Record one event. Never raises, never blocks the caller's flow."""
        try:
            self._repo.save({
                'event': event,
                'telegram_id': telegram_id,
                'created_at': datetime.now(timezone.utc),
                'props': _scrub(event, props),
            })
        except Exception:
            logger.exception('Failed to record analytics event %r', event)

    def recent_for_user(self, telegram_id: int, limit: int = 50) -> list:
        return self._repo.find_recent(telegram_id, limit)


def _scrub(event: str, props: dict) -> dict:
    """Drop anything that looks like free text before it reaches the database."""
    clean = {}
    for key, value in props.items():
        if isinstance(value, str) and len(value) > _MAX_PROP_CHARS:
            logger.warning(
                'Dropped analytics prop %r on event %r: %d chars is prose, not a label.',
                key, event, len(value),
            )
            continue
        clean[key] = value
    return clean
