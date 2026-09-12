# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

AnxietyJournal — a private Telegram chatbot that helps users externalise and process anxiety through daily check-ins. The bot asks how they're feeling, listens to their response, replies empathetically via LLM, and over time surfaces patterns in their mood and triggers. Written in Python using `python-telegram-bot` v20+ (async), calling Claude API for LLM responses, and MongoDB for persistence.

## Commands

```bash
# Run the bot
python main.py

# Via Docker
docker-compose up

# Lint / format
flake8
black .

# Run tests (Python 3.11+; runtime deps are in requirements.txt)
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## Architecture

```
User (Telegram) → Handlers → Services → LLM / DB
```

**Entry point**: `main.py` — builds the Telegram `Application`, registers handlers, calls `run_polling()`.

**Async rule**: handlers and scheduler callbacks are coroutines sharing one event loop. The services stay
synchronous, so every call into them from a handler or the scheduler tick goes through `asyncio.to_thread`.
A blocking Anthropic or pymongo call left on the loop stalls the bot for every user, not just the caller.

**Conversation flow** (`bot/handlers/journal.py`):

- `ONBOARDING_NAME` → `ONBOARDING_TIMEZONE` → `ONBOARDING_TIME`: first-time setup, collects name, timezone, reminder time, saves to DB with `onboarded=True`
- `MAIN_MENU`: persistent menu (Check In, History, Stats, Help)
- `CHECK_IN_MOOD`: user rates mood 1–10
- `CHECK_IN_TEXT`: user writes journal entry → LLM extracts tags, generates empathetic response → entry saved → streak updated

**Layers**:
| Directory | Role |
|---|---|
| `bot/handlers/` | Telegram command and conversation handlers |
| `bot/keyboards.py` | ReplyKeyboard definitions (main menu, mood 1–10) |
| `services/` | Business logic — `LlmService`, `UserService`, `JournalService`, `SchedulerService` (stub) |
| `repositories/` | MongoDB data access — `UserRepository`, `EntryRepository`, `StreakRepository` |
| `db/db.py` | MongoDB connection and collection accessors |
| `messages/strings.py` | All user-facing message templates |

**LLM integration** (`LlmService`):

- `get_empathetic_response(mood_score, entry_text)` — 2-3 paragraph empathetic reply
- `extract_tags(entry_text)` — returns up to 5 comma-separated theme tags
- `get_weekly_summary(entries)` — weekly pattern summary (Phase 4)
- Model is configured via `ANTHROPIC_MODEL` (default `claude-3-5-sonnet-latest`), `max_tokens=512`

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
- **Phase 3 — Scheduler**: stub (`SchedulerService`) — daily reminders, streak milestones
- **Phase 4 — Insights**: not started — weekly summary, tag patterns, mood trends
- **Phase 5 — Polish**: not started — `/history`, `/stats` commands, error handling
