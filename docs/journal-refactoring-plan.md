# Refactoring Plan — `bot/handlers/journal.py`

_Written 2026-09-13. Scope: split the journal conversation module into a package. Behaviour-preserving; no product change. Companion to [engineering-plan.md](engineering-plan.md), which holds the phase sequencing — this file covers one internal refactor and does not move a phase boundary._

All claims below are anchored to `file:line` against `journal.py` as of commit `9d58e36`, so they stay checkable as the code moves. Where a line reference no longer matches, trust the code.

## 1. Context

`bot/handlers/journal.py` is 478 lines — by far the largest source file in the repo (next largest is `messages/strings.py` at 172). It has accreted six unrelated responsibilities behind one module name: onboarding, IANA timezone resolution, the main-menu router, the check-in flow, three read-only views, and Markdown escaping — plus the `ConversationHandler` wiring that is its only real reason to exist as a single unit.

The cost is concrete, not stylistic:

- **Duplication that has already diverged.** `journal.py:78` and `services/scheduler_service.py:19` are two different `_escape_md` implementations. The scheduler's version chains `.replace()` over `('*', '_', '`', '[')`, so it re-escapes the backslashes it just inserted — a latent bug the regex version in `journal.py` does not have. `_MIN_ENTRIES_FOR_LLM_SUMMARY = 3` (`journal.py:358`) and `_MIN_ENTRIES_FOR_WEEKLY_SUMMARY = 3` (`scheduler_service.py:16`) are the same rule written twice.
- **Duplication inside the file.** `_user_timezone()` (`journal.py:361`) fetches the user and resolves their timezone; `show_weekly_summary` (`journal.py:376-378`) does the same work inline because it also needs the raw IANA name. The four-line `try / log / ERROR_GENERIC / return MAIN_MENU` block appears four times.
- **A magic literal shadowing its own constant.** `journal.py:296` writes `mood_score <= 2` where `CRISIS_MOOD_THRESHOLD` is defined at `journal.py:104`.
- **Constants declared mid-file.** `_MIN_ENTRIES_FOR_LLM_SUMMARY` sits at line 358, 250 lines below the other module constants.
- **A test file locked to the module's internals.** `tests/test_handlers.py` (786 lines) carries **52** `patch('bot.handlers.journal.<singleton>')` strings, because the doubles are rebuilt inline in every test instead of coming from a fixture.

Intended outcome: `bot/handlers/journal/__init__.py` becomes a thin orchestrator that owns only the conversation state machine and `register()`. Each responsibility gets its own module with one reason to change. No behaviour changes, and the deliberate design decisions in the current file — the visible `asyncio.to_thread` boundary, the crisis-resource ordering — are preserved verbatim and called out in §4 so they survive the move.

## 2. Target layout

```
messages/markdown.py                  escape_md  (shared by bot/ and services/)

bot/handlers/journal/
├── __init__.py     orchestrator: ConversationHandler, register(), public re-exports
├── states.py       the 7 conversation-state ints + mood thresholds
├── deps.py         service singletons — the single patch point
├── errors.py       @service_errors decorator
├── timezones.py    TimezoneFinder + IANA fuzzy search (pure, no telegram imports)
├── onboarding.py   start, handle_name, handle_timezone, handle_timezone_location,
│                   handle_reminder_time
├── menu.py         handle_main_menu, cancel
├── checkin.py      handle_mood, handle_entry_text, handle_guidance_offer, crisis resources
└── views.py        show_history, show_stats, show_weekly_summary, mood_bar
```

Dependency direction is acyclic, and **no submodule may import the package `__init__`**:

```
__init__   →  onboarding, menu, checkin, views
menu       →  views
onboarding →  timezones
(all)      →  states, deps, errors, messages.markdown
timezones  →  stdlib + timezonefinder only
```

A package, rather than flat sibling modules under `bot/handlers/`, because these pieces are internals of one conversation rather than peers of `commands.py`. The package name is unchanged, so `main.py:21,36` and `bot/handlers/__init__.py` (`from . import commands, journal`) keep working untouched.

`escape_md` lands in `messages/markdown.py` rather than inside the journal package because `services/scheduler_service.py` needs it too, and a service importing from `bot/handlers/` would invert the layering. `messages/` is already the shared presentation layer the scheduler imports from (`messages.strings`), so it is the natural home. That leaves `mood_bar` as the only would-be occupant of a `rendering.py`, so it lives in `views.py`, its sole caller.

## 3. Step 1 — Extract the shared helpers

Do this first. It stands alone, touches no handler, and fixes the escaping bug.

1. New `messages/markdown.py` with the regex implementation lifted from `journal.py:75-80`, renamed public: `_MD_SPECIAL = re.compile(r'([_*`\[])')` and `escape_md(text: str) -> str`. Keep the existing docstring. (`messages/` is a namespace package with no `__init__.py`, consistent with `messages/strings.py`.)
2. Delete `_escape_md` from `services/scheduler_service.py:19-22` and from `journal.py`; both import `from messages.markdown import escape_md`.
3. Move the min-entries rule to one public constant, `MIN_ENTRIES_FOR_WEEKLY_SUMMARY = 3`, at the top of `services/journal_service.py` — it is a rule about journal entries, and `JournalService` owns `get_weekly_entries`. Import it in `scheduler_service.py` and later in `views.py`; delete both private copies.

Run `pytest` here. The scheduler's escaping behaviour changes for input containing a backslash, so if any test in `tests/test_scheduler_service.py` asserts the old double-escaped output, correct the expectation and note it in the commit message — that is a bug fix, not a regression.

## 4. Step 2 — Create the package skeleton

```bash
mkdir bot/handlers/journal
git mv bot/handlers/journal.py bot/handlers/journal/__init__.py
```

`git mv` so the file's history follows it.

Then carve out submodules **one at a time, running `pytest` after each**, in the order below. Each carve is a pure move: copy the definitions out, delete them from `__init__.py`, add the import back.

**`states.py`** — the `range(7)` state tuple (`journal.py:93-101`), `LOW_MOOD_THRESHOLD`, `CRISIS_MOOD_THRESHOLD`. No imports beyond stdlib.

**`deps.py`** — the three singletons from `journal.py:106-108`, renamed without the leading underscore since they are now this module's public surface:

```python
"""Service singletons shared by the journal handlers.

Reach services through this module's attributes — `deps.llm_svc.extract_tags(...)`, never
`from .deps import llm_svc`. A value import binds the real service into the importing module,
where `patch('bot.handlers.journal.deps.llm_svc')` cannot reach it: the patch succeeds, the
handler keeps the real object, and the test passes while hitting a live Anthropic client.
Attribute access keeps one patch point for every handler.
"""
from services.journal_service import JournalService
from services.llm_service import LlmService
from services.user_service import UserService

user_svc = UserService()
journal_svc = JournalService()
llm_svc = LlmService()
```

That docstring is the single most important line in this refactor — the failure mode it describes is a *passing* test that silently reaches a live service. See the guard test in §6.5.

**`errors.py`** — collapses the block repeated at `journal.py:305-311`, `:331-336` and `:382-385`:

```python
def service_errors(what: str):
    """Return the user to the main menu with a generic apology if a service call fails."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(update, context):
            try:
                return await fn(update, context)
            except Exception:
                logger.exception('%s failed for user %s', what, update.effective_user.id)
                await update.message.reply_text(ERROR_GENERIC, reply_markup=get_main_menu_keyboard())
                return MAIN_MENU
        return wrapper
    return decorator
```

**`timezones.py`** — `_tf = TimezoneFinder()`, `_ALL_TIMEZONES`, `_search_timezones` (`journal.py:83-90`), plus a new `detect_timezone(lat, lng)` wrapping `_tf.timezone_at`. Keep `_tf` as a module-level name; the five `TestHandleTimezoneLocation` tests patch it. Nothing from `telegram` belongs here — this module should be testable without an `Update`.

Do **not** add a timezone-resolution helper here: `services/time_utils.resolve_timezone(name, telegram_id)` already exists and is already used at `journal.py:365,378`. Keep importing it.

**`views.py`, `onboarding.py`, `checkin.py`, `menu.py`** — move the handlers as-is, then apply the §5 cleanups.

**`__init__.py`** — what remains: the module docstring (§7), imports of the handlers, `register()`, and an `__all__` re-exporting the real public surface (the 7 states, the 9 handlers, `register`). `mood_bar` is *not* re-exported; its test imports it from `views` directly.

## 5. Step 3 — Targeted cleanups during the move

These are the reasons the split is worth doing; do them as part of the carve, not afterwards.

- **`views.py`** — decorate `show_history`, `show_stats` and `show_weekly_summary` with `@service_errors('History')` / `('Stats')` / `('Weekly summary')` and delete their `try`/`except` blocks. Complexity drops from 5 / – / 6 to roughly 3.
- **`views.py`** — make `_user_timezone` return both values it already computes, so `show_weekly_summary` stops re-fetching the user:

  ```python
  async def _user_timezone(telegram_id: int) -> tuple[str | None, tzinfo]:
      """The user's stored IANA name (if any) and the resolved tzinfo."""
      user = await asyncio.to_thread(deps.user_svc.get, telegram_id) or {}
      name = user.get('timezone')
      return name, resolve_timezone(name, telegram_id)
  ```

  `show_history` uses `_, tz = await _user_timezone(...)`; `show_weekly_summary` uses `name, tz` and passes `name` to `get_weekly_entries`. Add the missing return type hint while here.
- **`views.py`** — rename `_mood_bar` to `mood_bar` (now this module's tested public surface) and take `MIN_ENTRIES_FOR_WEEKLY_SUMMARY` from `services.journal_service`.
- **`checkin.py`** — replace the literal at `journal.py:296` with the existing constant: `offer = GUIDANCE_OFFER_VERY_LOW if mood_score <= CRISIS_MOOD_THRESHOLD else GUIDANCE_OFFER_LOW`.

### Two things that must NOT change

1. **`handle_entry_text` keeps its narrow `try` block and its ordering.** Do *not* wrap it in `@service_errors`. The crisis-resource send at `journal.py:275-276` is deliberately *before* the `try`, and the guidance offer at `:294-298` deliberately *after* it — the comment at `:272-274` explains why. Widening the guarded region would let a failed crisis-resource send collapse into a generic error message. This is the one safety-critical ordering in the file; preserve the comment verbatim.
2. **The `asyncio.to_thread` boundary stays at each call site.** CLAUDE.md states the boundary is "deliberate and visible". Do not hide the wrapping inside `deps` behind async proxy methods — `await asyncio.to_thread(deps.llm_svc.extract_tags, text)` stays written out in the handler.

## 6. Step 4 — Tests

`tests/test_handlers.py` is the only test file affected; the other four (851 lines) are untouched.

1. **Retarget the 52 patch strings.** Mechanical: `bot.handlers.journal._journal_svc` → `bot.handlers.journal.deps.journal_svc` (23 sites), `._llm_svc` → `.deps.llm_svc` (18), `._user_svc` → `.deps.user_svc` (6), `._tf` → `.timezones._tf` (5).
2. **The top-level import block (`tests/test_handlers.py:13-32`) needs only one change** — `_mood_bar` becomes `from bot.handlers.journal.views import mood_bar`. Everything else still resolves through the package's `__all__`.
3. **`TestHandlersAreCoroutines` (`:756-786`)** reaches `journal.handle_name`, `journal.handle_main_menu`, `journal.cancel`, `journal.register` as attributes — all still present via the facade. Its `assert app.add_handler.call_count == 3` still holds: `register()` adds exactly one `ConversationHandler`, as today.
4. **Promote the shared doubles into `tests/conftest.py`** — `_update`, `_location_update`, `_context` (`:41-61`) as fixtures/factories, plus `mock_journal_svc`, `mock_llm_svc`, `mock_user_svc` fixtures wrapping the patches. This is what removes the pressure that produced 52 hardcoded strings. Keep the existing autouse `mock_db` fixture as-is.
5. **Add a guard test** so the value-import hazard cannot regress silently:

   ```python
   def test_submodules_never_value_import_the_singletons():
       """Handlers must reach services as `deps.llm_svc`, or patching deps silently no-ops."""
       for path in Path('bot/handlers/journal').glob('*.py'):
           src = path.read_text()
           assert 'from .deps import' not in src
           assert 'from bot.handlers.journal.deps import' not in src
   ```

## 7. Step 5 — Documentation

The 9-line module docstring at `journal.py:1-9` explains the event-loop / `to_thread` contract and is the only place it is written down outside CLAUDE.md. Move it to `bot/handlers/journal/__init__.py`, extended with a short map of the submodules, and add a one-line pointer at the top of each submodule that calls a service (`onboarding`, `checkin`, `views`):

```python
"""...  Service calls go through `asyncio.to_thread` — see the package docstring."""
```

Update CLAUDE.md: the Architecture section's `bot/handlers/journal.py` reference and the conversation-flow list. Separately, while in that file — **Phase 3 is recorded as a stub, but `SchedulerService` is fully implemented** (reminders, weekly summaries, job-queue guard, 368 lines of tests). Correct that line.

## 8. Step 6 — Lock in the reduction

Add to the `[flake8]` block in `setup.cfg`:

```ini
max-complexity = 8
```

Verified: the repo passes at 8 **today** (`flake8 --max-complexity 8 .` is clean), so this is a ratchet that can land immediately rather than a target. Current peaks are `handle_main_menu`, `handle_entry_text` and `show_weekly_summary` at 6, and `SchedulerService._send_reminders` at 8.

Worth one line if tooling is touched: CLAUDE.md documents `black .`, but there is no black config, so black defaults to 88 columns against flake8's 120. Out of scope here — flagged so nobody runs `black .` mid-refactor and lands a reformatting diff on top of the move.

## 9. Verification

Run after **each** carve in §4, not just at the end:

```bash
.venv/bin/pytest -q          # 90 handler tests + 82 others must stay green
.venv/bin/flake8             # clean today; add max-complexity=8 in §8
```

Then confirm the refactor is behaviour-preserving:

1. **Registration is unchanged** — `python -c "import main"` imports cleanly (needs `CLAUDE_API_KEY` set to anything, as CI does, because `deps.py` still builds `LlmService()` at import time), and `TestHandlersAreCoroutines` still sees `add_handler.call_count == 3`.
2. **The patches actually bite** — the highest-value check. Temporarily make one service method raise, run `pytest -q`, and confirm the corresponding tests *fail*. If they still pass, a submodule is value-importing from `deps` and every mock in that area is inert. The §6.5 guard test should catch this, but verify it once by hand.
3. **Manual smoke** via `python main.py` against a test bot: `/start` through onboarding (try both a shared location and a typed city name such as `berlin`, to exercise the fuzzy path), a check-in at mood 8 (no guidance offer), a check-in at mood 2 (crisis resources sent *before* the LLM call, then the guidance offer), then History, Stats and Weekly Summary.
4. **Diff review** — `git diff -M --stat` should show renames and moves, with real logic changes confined to §5.

## 10. Commit sequence

Each commit is independently green and reviewable:

1. `Extract escape_md to messages/markdown.py` (fixes the scheduler's double-escaping)
2. `Share the weekly-summary minimum-entries rule`
3. `Move journal.py into a package` (pure `git mv`, no content change)
4. `Split the journal conversation into focused modules`
5. `Collapse repeated service-error handling into a decorator`
6. `Move handler test doubles into conftest fixtures`
7. `Gate cyclomatic complexity at 8`
