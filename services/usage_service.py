"""Per-user daily ceiling on Anthropic calls.

Nothing in this bot capped LLM work before: one check-in is two calls, guidance
is a third, and a weekly summary sends an entire week of entries as one prompt.
A user who checks in fifty times in an evening — bored, testing, or in genuine
distress — costs fifty times what a normal day costs, and nothing anywhere would
have said so.

The ceiling is deliberately loose. It exists to bound a runaway day, not to
ration normal use: the budget below is several times a heavy user's day, so
reaching it means something unusual is happening. Every call site degrades
rather than refuses — the entry is still saved, the trend is still drawn — so
the worst a user at their ceiling experiences is a bot that stops writing prose
back, never one that loses what they wrote.

The day is the user's *local* day, so the reset lands at their midnight rather
than somewhere in their afternoon. An unusable timezone falls back to UTC, which
`time_utils.resolve_timezone` already does: unlike a scheduled send, guessing
wrong here shifts a budget window and wakes nobody up.

This service resolves that timezone itself rather than taking it as an argument
from each caller. The day key has to be identical across every surface — if the
check-in path keyed on UTC and the summary path on local time, one user would
hold two counters either side of midnight and get twice the budget. Callers that
already hold the user record can pass `timezone_name` to skip the lookup; the
answer is the same either way.
"""
from __future__ import annotations

import logging

from repositories.usage_repo import UsageRepository
from repositories.user_repo import UserRepository
from services import time_utils

logger = logging.getLogger(__name__)

# Anthropic calls per user per local day. A heavy but ordinary day — three
# check-ins with guidance and a summary view — is around a dozen.
DAILY_LLM_CALL_BUDGET = 40

_LLM_CALLS = 'llm_calls'


class UsageService:
    def __init__(self):
        self._repo = UsageRepository()
        self._users = UserRepository()

    def consume_llm(self, telegram_id: int, calls: int = 1, timezone_name: str = None) -> bool:
        """Reserve `calls` against today's budget. True if they may proceed.

        Reserves before the work rather than counting after it, so two
        overlapping check-ins cannot both pass the check. A refused reservation
        is handed back, which keeps the stored counter a true record of calls
        actually made — it doubles as the per-user spend metric, and inflating
        it with attempts that never reached Anthropic would make that useless.
        """
        day = self._today(telegram_id, timezone_name)
        used = self._repo.increment(telegram_id, day, _LLM_CALLS, calls)
        if used <= DAILY_LLM_CALL_BUDGET:
            return True

        self._repo.increment(telegram_id, day, _LLM_CALLS, -calls)
        logger.warning(
            'User %s is at the daily LLM ceiling (%d calls) — degrading this request.',
            telegram_id, DAILY_LLM_CALL_BUDGET,
        )
        return False

    def used_today(self, telegram_id: int, timezone_name: str = None) -> int:
        doc = self._repo.get(telegram_id, self._today(telegram_id, timezone_name))
        return (doc or {}).get(_LLM_CALLS, 0)

    def _today(self, telegram_id: int, timezone_name: str = None) -> str:
        if timezone_name is None:
            timezone_name = (self._users.find(telegram_id) or {}).get('timezone')
        tz = time_utils.resolve_timezone(timezone_name, telegram_id)
        return time_utils.now().astimezone(tz).date().isoformat()
