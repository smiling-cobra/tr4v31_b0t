# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

AnxietyJournal — a private Telegram chatbot that helps users externalise and process anxiety through daily check-ins. The bot asks how they're feeling, listens to their response, replies empathetically via LLM, and over time surfaces patterns in their mood and triggers. Written in Python using `python-telegram-bot` v13, calling Claude API for LLM responses, and MongoDB for persistence.

## Commands

```bash
# Run the bot
python main.py

# Via Docker
docker-compose up

# Lint / format
flake8
black .

# Run tests
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest
```

## Architecture

```
User (Telegram) → Handlers → Services → LLM / DB
```

**Entry point**: `main.py` — creates the Telegram `Updater`, registers handlers, starts polling.

**Conversation flow** (`bot/handlers/journal.py`):

- `ONBOARDING_NAME` → `ONBOARDING_TIMEZONE` → `ONBOARDING_TIME`: first-time setup, collects name, timezone, reminder time, saves to DB with `onboarded=True`
- `MAIN_MENU`: persistent menu (Check In, History, Stats, Weekly Summary, Help)
- `CHECK_IN_MOOD`: user rates mood 1–10
- `CHECK_IN_TEXT`: user writes journal entry → LLM extracts tags, generates empathetic response → entry saved → streak updated
- `CHECK_IN_GUIDANCE_OFFER`: entered only when mood ≤ `LOW_MOOD_THRESHOLD` (4) — offers coping guidance, appends crisis resources at ≤ 2, otherwise returns to `MAIN_MENU`

**Layers**:
| Directory | Role |
|---|---|
| `bot/handlers/` | Telegram command and conversation handlers |
| `bot/keyboards.py` | ReplyKeyboard definitions (main menu, mood 1–10) |
| `services/` | Business logic — `LlmService`, `UserService`, `JournalService`, `SchedulerService` |
| `repositories/` | MongoDB data access — `UserRepository`, `EntryRepository`, `StreakRepository` |
| `db/db.py` | MongoDB connection and collection accessors |
| `messages/strings.py` | All user-facing message templates |

**LLM integration** (`LlmService`):

- `get_empathetic_response(mood_score, entry_text)` — 2-3 paragraph empathetic reply
- `extract_tags(entry_text)` — returns up to 5 comma-separated theme tags
- `get_weekly_summary(entries)` — weekly pattern summary
- `get_psychological_guidance(mood_score, entry_text)` — opt-in coping suggestions for low mood; swaps technique sets by severity (DBT TIPP + ACT defusion at ≤ 2, otherwise behavioural activation / CBT / grounding), `max_tokens=600`
- Model is configured via `ANTHROPIC_MODEL` (default `claude-3-5-sonnet-latest`), `max_tokens=512`
- `_call` swallows every exception and returns a fallback sentence, so an API outage degrades the reply but never loses the entry

**Streak logic** (`JournalService._update_streak`): increments if last check-in was yesterday, resets to 1 if gap > 1 day, no-ops if already checked in today.

## Environment Variables (`.env`)

```
TELEGRAM_TOKEN
CLAUDE_API_KEY
MONGODB_URI
ANTHROPIC_MODEL (optional)
```

## Roadmap Status

- **Phase 1 — Foundation**: complete (onboarding, DB, bot skeleton)
- **Phase 2 — Core Loop**: complete (check-in, LLM response, entry saving, streak tracking)
- **Phase 3 — Scheduler**: complete — timezone-aware daily reminders (`SchedulerService`, 60s `job_queue` tick), duplicate suppression via `last_reminder_sent` on the user document. Streak milestones were dropped from scope and are not implemented.
- **Phase 4 — Insights**: complete — weekly summary with mood-trend bars, top tags, and an LLM synthesis (only when the week has ≥ 3 entries); scheduled weekly delivery, throttled to once per 7 days via `last_weekly_summary_sent`
- **Phase 5 — Polish**: complete — `/history`, `/stats`, `/summary` commands and `try`/`except` fallbacks to `ERROR_GENERIC` around every DB and LLM call in the handlers
- **Phase 6 — Low-mood guidance**: complete — opt-in coping guidance offered when mood ≤ 4 (`CHECK_IN_GUIDANCE_OFFER`), with crisis-resource text appended by application code, never by the LLM

**Known gaps** (not roadmap phases, just dead weight): `services/cache_service.py` is a leftover from the travel bot this repo was rewired from; `bot/handlers/group.py` and `repositories/notification_repo.py` are unimplemented stubs. `CONTEXT.md` holds the product-domain rules and is the companion to this file.
