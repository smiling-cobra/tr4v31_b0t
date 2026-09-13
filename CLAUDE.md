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
This keeps the loop responsive; it does not make updates concurrent. Updates are still processed one at a time.

**Conversation flow** (`bot/handlers/journal/`):

- `ONBOARDING_NAME` → `ONBOARDING_TIMEZONE` → `ONBOARDING_TIME`: first-time setup (`onboarding.py`), collects name, timezone, reminder time, saves to DB with `onboarded=True`
- `MAIN_MENU`: persistent menu (Check In, History, Stats, Weekly Summary, Help) — `menu.py`
- `CHECK_IN_MOOD`: user rates mood 1–10 — `checkin.py`
- `CHECK_IN_TEXT`: user writes journal entry → LLM extracts tags, generates empathetic response → entry saved → streak updated — `checkin.py`
- `CHECK_IN_GUIDANCE_OFFER`: on a low mood score, an opt-in offer of coping guidance — `checkin.py`

`bot/handlers/journal/__init__.py` is a thin orchestrator: the `ConversationHandler` wiring and
`register()`. Each responsibility lives in its own module — `states.py` (state ints and mood
thresholds), `deps.py` (service singletons, reached as `deps.llm_svc` etc.), `errors.py`
(`@service_errors`, the shared "fall back to main menu" decorator), `timezones.py` (IANA lookup),
and the read-only `views.py` (history, stats, weekly summary).

**Layers**:
| Directory | Role |
|---|---|
| `bot/handlers/` | Telegram command and conversation handlers |
| `bot/keyboards.py` | ReplyKeyboard definitions (main menu, mood 1–10) |
| `services/` | Business logic — `LlmService`, `UserService`, `JournalService`, `SchedulerService` |
| `repositories/` | MongoDB data access — `UserRepository`, `EntryRepository`, `StreakRepository` |
| `db/db.py` | MongoDB connection and collection accessors |
| `messages/strings.py` | All user-facing message templates |
| `messages/markdown.py` | `escape_md` — Markdown v1 escaping, shared by `bot/` and `services/` |

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
- **Phase 3 — Scheduler**: complete (`SchedulerService`) — daily reminders and weekly-summary delivery, gated on `Application.job_queue`
- **Phase 4 — Insights**: not started — weekly summary, tag patterns, mood trends
- **Phase 5 — Polish**: not started — `/history`, `/stats` commands, error handling
