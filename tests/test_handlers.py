"""Tests for handler input validation.

Strategy: call handler functions directly with mocked Update / CallbackContext
and assert the returned conversation-state integer. No Telegram API is hit.
LLM and DB calls are patched wherever a handler reaches them.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from datetime import datetime

from bot.handlers.journal import (
    _mood_bar,
    CHECK_IN_GUIDANCE_OFFER,
    CHECK_IN_MOOD,
    CHECK_IN_TEXT,
    MAIN_MENU,
    ONBOARDING_NAME,
    ONBOARDING_TIME,
    ONBOARDING_TIMEZONE,
    handle_entry_text,
    handle_guidance_offer,
    handle_mood,
    handle_reminder_time,
    handle_timezone,
    handle_timezone_location,
    show_history,
    show_stats,
    show_weekly_summary,
    start,
)
from messages.strings import GUIDANCE_CRISIS_RESOURCES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update(text: str, user_id: int = 12345) -> MagicMock:
    u = MagicMock()
    u.message.text = text
    u.message.reply_text = AsyncMock()
    u.effective_user.id = user_id
    return u


def _location_update(lat: float, lng: float, user_id: int = 12345) -> MagicMock:
    u = MagicMock()
    u.message.location.latitude = lat
    u.message.location.longitude = lng
    u.message.reply_text = AsyncMock()
    u.effective_user.id = user_id
    return u


def _context(user_data: dict | None = None) -> MagicMock:
    c = MagicMock()
    c.user_data = user_data if user_data is not None else {}
    return c


# ---------------------------------------------------------------------------
# Timezone validation
# ---------------------------------------------------------------------------

class TestHandleTimezone:
    # --- exact IANA match ---

    async def test_valid_iana_timezone_advances_state(self):
        ctx = _context({'name': 'Alice'})
        result = await handle_timezone(_update('Europe/London'), ctx)
        assert result == ONBOARDING_TIME

    async def test_valid_timezone_stored_in_user_data(self):
        ctx = _context({'name': 'Alice'})
        await handle_timezone(_update('America/New_York'), ctx)
        assert ctx.user_data['timezone'] == 'America/New_York'

    async def test_utc_is_accepted(self):
        ctx = _context({'name': 'Alice'})
        result = await handle_timezone(_update('UTC'), ctx)
        assert result == ONBOARDING_TIME

    # --- fuzzy single-match: auto-accept ---

    async def test_city_name_single_match_advances_state(self):
        # "London" uniquely matches Europe/London
        ctx = _context({'name': 'Alice'})
        result = await handle_timezone(_update('London'), ctx)
        assert result == ONBOARDING_TIME

    async def test_city_name_single_match_stores_timezone(self):
        ctx = _context({'name': 'Alice'})
        await handle_timezone(_update('London'), ctx)
        assert ctx.user_data['timezone'] == 'Europe/London'

    async def test_city_name_case_insensitive(self):
        ctx = _context({'name': 'Alice'})
        result = await handle_timezone(_update('london'), ctx)
        assert result == ONBOARDING_TIME

    async def test_city_name_space_normalized(self):
        # "New York" → needle "new_york" → America/New_York
        ctx = _context({'name': 'Alice'})
        result = await handle_timezone(_update('New York'), ctx)
        assert result == ONBOARDING_TIME
        assert ctx.user_data['timezone'] == 'America/New_York'

    async def test_valid_iana_timezone_removes_keyboard(self):
        from telegram import ReplyKeyboardRemove
        update = _update('Europe/London')
        await handle_timezone(update, _context({'name': 'Alice'}))
        assert any(
            isinstance(call.kwargs.get('reply_markup'), ReplyKeyboardRemove)
            for call in update.message.reply_text.call_args_list
        )

    async def test_city_name_single_match_removes_keyboard(self):
        from telegram import ReplyKeyboardRemove
        update = _update('London')
        await handle_timezone(update, _context({'name': 'Alice'}))
        assert any(
            isinstance(call.kwargs.get('reply_markup'), ReplyKeyboardRemove)
            for call in update.message.reply_text.call_args_list
        )

    # --- fuzzy multi-match (2-5): show keyboard, stay ---

    async def test_city_name_multiple_matches_stays_on_timezone(self):
        # "Kentucky" matches America/Kentucky/Louisville and America/Kentucky/Monticello
        result = await handle_timezone(_update('Kentucky'), _context({'name': 'Alice'}))
        assert result == ONBOARDING_TIMEZONE

    # --- no match or too many matches: error, stay ---

    async def test_unknown_input_stays_on_timezone(self):
        result = await handle_timezone(_update('Mars/Olympus'), _context({'name': 'Alice'}))
        assert result == ONBOARDING_TIMEZONE

    async def test_too_many_matches_stays_on_timezone(self):
        # "north" appears in many zone names (>5)
        result = await handle_timezone(_update('north'), _context({'name': 'Alice'}))
        assert result == ONBOARDING_TIMEZONE


# ---------------------------------------------------------------------------
# Timezone via location sharing
# ---------------------------------------------------------------------------

class TestHandleTimezoneLocation:
    async def test_valid_location_advances_state(self):
        ctx = _context({'name': 'Alice'})
        with patch('bot.handlers.journal._tf') as mock_tf:
            mock_tf.timezone_at.return_value = 'Europe/Berlin'
            result = await handle_timezone_location(_location_update(52.52, 13.405), ctx)
        assert result == ONBOARDING_TIME

    async def test_valid_location_stores_timezone(self):
        ctx = _context({'name': 'Alice'})
        with patch('bot.handlers.journal._tf') as mock_tf:
            mock_tf.timezone_at.return_value = 'Europe/Berlin'
            await handle_timezone_location(_location_update(52.52, 13.405), ctx)
        assert ctx.user_data['timezone'] == 'Europe/Berlin'

    async def test_valid_location_removes_keyboard(self):
        from telegram import ReplyKeyboardRemove
        update = _location_update(52.52, 13.405)
        with patch('bot.handlers.journal._tf') as mock_tf:
            mock_tf.timezone_at.return_value = 'Europe/Berlin'
            await handle_timezone_location(update, _context({'name': 'Alice'}))
        assert any(
            isinstance(call.kwargs.get('reply_markup'), ReplyKeyboardRemove)
            for call in update.message.reply_text.call_args_list
        )

    async def test_unresolvable_location_stays_on_timezone(self):
        # timezonefinder returns None for open ocean coordinates
        ctx = _context({'name': 'Alice'})
        with patch('bot.handlers.journal._tf') as mock_tf:
            mock_tf.timezone_at.return_value = None
            result = await handle_timezone_location(_location_update(0.0, 0.0), ctx)
        assert result == ONBOARDING_TIMEZONE

    async def test_unresolvable_location_does_not_store_timezone(self):
        ctx = _context({'name': 'Alice'})
        with patch('bot.handlers.journal._tf') as mock_tf:
            mock_tf.timezone_at.return_value = None
            await handle_timezone_location(_location_update(0.0, 0.0), ctx)
        assert 'timezone' not in ctx.user_data


# ---------------------------------------------------------------------------
# Reminder time validation
# ---------------------------------------------------------------------------

class TestHandleReminderTime:
    def _ctx(self) -> MagicMock:
        return _context({'name': 'Alice', 'timezone': 'Europe/London'})

    async def test_valid_time_advances_to_main_menu(self):
        with patch('bot.handlers.journal._user_svc'):
            result = await handle_reminder_time(_update('09:00'), self._ctx())
        assert result == MAIN_MENU

    async def test_valid_time_saves_user(self):
        with patch('bot.handlers.journal._user_svc') as mock_svc:
            await handle_reminder_time(_update('21:30'), self._ctx())
        mock_svc.create_or_update.assert_called_once()

    async def test_no_colon_stays(self):
        result = await handle_reminder_time(_update('0900'), self._ctx())
        assert result == ONBOARDING_TIME

    async def test_letters_stay(self):
        result = await handle_reminder_time(_update('nine'), self._ctx())
        assert result == ONBOARDING_TIME

    async def test_hour_25_stays(self):
        result = await handle_reminder_time(_update('25:00'), self._ctx())
        assert result == ONBOARDING_TIME

    async def test_minute_60_stays(self):
        result = await handle_reminder_time(_update('09:60'), self._ctx())
        assert result == ONBOARDING_TIME

    async def test_boundary_midnight(self):
        with patch('bot.handlers.journal._user_svc'):
            result = await handle_reminder_time(_update('00:00'), self._ctx())
        assert result == MAIN_MENU

    async def test_boundary_last_minute_of_day(self):
        with patch('bot.handlers.journal._user_svc'):
            result = await handle_reminder_time(_update('23:59'), self._ctx())
        assert result == MAIN_MENU


# ---------------------------------------------------------------------------
# Mood score validation
# ---------------------------------------------------------------------------

class TestHandleMood:
    async def test_valid_score_advances_state(self):
        ctx = _context({'name': 'Alice'})
        result = await handle_mood(_update('7'), ctx)
        assert result == CHECK_IN_TEXT

    async def test_score_stored_in_user_data(self):
        ctx = _context({'name': 'Alice'})
        await handle_mood(_update('7'), ctx)
        assert ctx.user_data['mood_score'] == 7

    async def test_lower_boundary_accepted(self):
        result = await handle_mood(_update('1'), _context({'name': 'A'}))
        assert result == CHECK_IN_TEXT

    async def test_upper_boundary_accepted(self):
        result = await handle_mood(_update('10'), _context({'name': 'A'}))
        assert result == CHECK_IN_TEXT

    async def test_zero_is_rejected(self):
        result = await handle_mood(_update('0'), _context())
        assert result == CHECK_IN_MOOD

    async def test_eleven_is_rejected(self):
        result = await handle_mood(_update('11'), _context())
        assert result == CHECK_IN_MOOD

    async def test_non_digit_is_rejected(self):
        result = await handle_mood(_update('bad'), _context())
        assert result == CHECK_IN_MOOD

    async def test_float_is_rejected(self):
        result = await handle_mood(_update('7.5'), _context())
        assert result == CHECK_IN_MOOD

    async def test_empty_string_is_rejected(self):
        result = await handle_mood(_update(''), _context())
        assert result == CHECK_IN_MOOD


# ---------------------------------------------------------------------------
# Phase 5 — check-in error handling
# ---------------------------------------------------------------------------

class TestHandleEntryTextErrors:
    def _ctx(self, mood_score: int = 7) -> MagicMock:
        return _context({'name': 'Alice', 'mood_score': mood_score})

    async def test_db_error_returns_main_menu(self):
        ctx = self._ctx()
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc'):
            mock_svc.save_entry.side_effect = Exception('DB down')
            result = await handle_entry_text(_update('feeling bad'), ctx)
        assert result == MAIN_MENU

    async def test_db_error_sends_error_message(self):
        ctx = self._ctx()
        update = _update('feeling bad')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc'):
            mock_svc.save_entry.side_effect = Exception('DB down')
            await handle_entry_text(update, ctx)
        from messages.strings import ERROR_GENERIC
        assert update.message.reply_text.call_args.args[0] == ERROR_GENERIC


class TestShowHistory:
    async def test_empty_history_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_recent_entries.return_value = []
            result = await show_history(_update(''), _context())
        assert result == MAIN_MENU

    async def test_db_error_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_recent_entries.side_effect = Exception('DB down')
            result = await show_history(_update(''), _context())
        assert result == MAIN_MENU

    async def test_db_error_sends_error_message(self):
        update = _update('')
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_recent_entries.side_effect = Exception('DB down')
            await show_history(update, _context())
        from messages.strings import ERROR_GENERIC
        assert update.message.reply_text.call_args.args[0] == ERROR_GENERIC


class TestShowStats:
    async def test_no_entries_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_stats.return_value = {'total': 0, 'streak': 0, 'avg_mood': 0}
            mock_svc.get_recent_entries.return_value = []
            result = await show_stats(_update(''), _context())
        assert result == MAIN_MENU

    async def test_db_error_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_stats.side_effect = Exception('DB down')
            result = await show_stats(_update(''), _context())
        assert result == MAIN_MENU

    async def test_db_error_sends_error_message(self):
        update = _update('')
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_stats.side_effect = Exception('DB down')
            await show_stats(update, _context())
        from messages.strings import ERROR_GENERIC
        assert update.message.reply_text.call_args.args[0] == ERROR_GENERIC


# ---------------------------------------------------------------------------
# Phase 4 — mood bar helper
# ---------------------------------------------------------------------------

class TestMoodBar:
    def test_score_0_all_empty(self):
        assert _mood_bar(0) == '░░░░░░░░░░'

    def test_score_10_all_filled(self):
        assert _mood_bar(10) == '▓▓▓▓▓▓▓▓▓▓'

    def test_score_5_half_filled(self):
        assert _mood_bar(5) == '▓▓▓▓▓░░░░░'

    def test_total_length_always_10(self):
        for score in range(0, 11):
            assert len(_mood_bar(score)) == 10

    def test_clamps_below_zero(self):
        assert _mood_bar(-1) == '░░░░░░░░░░'

    def test_clamps_above_ten(self):
        assert _mood_bar(11) == '▓▓▓▓▓▓▓▓▓▓'


# ---------------------------------------------------------------------------
# Phase 4 — weekly summary
# ---------------------------------------------------------------------------

def _entry(mood: int, days_ago: int = 0) -> dict:
    return {
        'mood_score': mood,
        'text': 'entry text',
        'tags': ['work', 'stress'],
        'created_at': datetime(2026, 3, 29 - days_ago, 10, 0),
    }


class TestShowWeeklySummary:
    async def test_no_entries_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_weekly_entries.return_value = []
            result = await show_weekly_summary(_update(''), _context())
        assert result == MAIN_MENU

    async def test_no_entries_sends_empty_message(self):
        update = _update('')
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_weekly_entries.return_value = []
            await show_weekly_summary(update, _context())
        from messages.strings import WEEKLY_SUMMARY_EMPTY
        assert update.message.reply_text.call_args.args[0] == WEEKLY_SUMMARY_EMPTY

    async def test_with_entries_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_svc.get_weekly_entries.return_value = [_entry(7), _entry(5, 1), _entry(3, 2)]
            mock_llm.get_weekly_summary.return_value = 'A good week overall.'
            result = await show_weekly_summary(_update(''), _context())
        assert result == MAIN_MENU

    async def test_message_contains_mood_scores(self):
        update = _update('')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_svc.get_weekly_entries.return_value = [_entry(7), _entry(5, 1)]
            mock_llm.get_weekly_summary.return_value = 'Summary.'
            await show_weekly_summary(update, _context())
        text = update.message.reply_text.call_args.args[0]
        assert '7' in text
        assert '5' in text

    async def test_message_contains_mood_bar(self):
        update = _update('')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_svc.get_weekly_entries.return_value = [_entry(5)]
            mock_llm.get_weekly_summary.return_value = 'Summary.'
            await show_weekly_summary(update, _context())
        text = update.message.reply_text.call_args.args[0]
        assert '▓' in text

    async def test_enough_entries_calls_llm_summary(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_svc.get_weekly_entries.return_value = [_entry(7), _entry(5, 1), _entry(3, 2)]
            mock_llm.get_weekly_summary.return_value = 'Summary.'
            await show_weekly_summary(_update(''), _context())
        mock_llm.get_weekly_summary.assert_called_once()

    async def test_too_few_entries_skips_llm_summary(self):
        update = _update('')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_svc.get_weekly_entries.return_value = [_entry(5), _entry(4, 1)]
            await show_weekly_summary(update, _context())
        mock_llm.get_weekly_summary.assert_not_called()
        from messages.strings import WEEKLY_SUMMARY_TOO_FEW
        assert WEEKLY_SUMMARY_TOO_FEW in update.message.reply_text.call_args.args[0]

    async def test_db_error_returns_main_menu(self):
        with patch('bot.handlers.journal._journal_svc') as mock_svc:
            mock_svc.get_weekly_entries.side_effect = Exception('DB down')
            result = await show_weekly_summary(_update(''), _context())
        assert result == MAIN_MENU


# ---------------------------------------------------------------------------
# Phase 6 — guidance offer trigger
# ---------------------------------------------------------------------------

class TestHandleEntryTextGuidance:
    async def _run(self, mood_score: int) -> tuple:
        ctx = _context({'name': 'Alice', 'mood_score': mood_score})
        update = _update('I feel awful')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_svc.get_stats.return_value = {'streak': 1, 'total': 1, 'avg_mood': mood_score}
            mock_llm.extract_tags.return_value = []
            mock_llm.get_empathetic_response.return_value = 'Hang in there.'
            result = await handle_entry_text(update, ctx)
        return result, ctx

    async def test_score_5_returns_main_menu(self):
        result, _ = await self._run(5)
        assert result == MAIN_MENU

    async def test_score_10_returns_main_menu(self):
        result, _ = await self._run(10)
        assert result == MAIN_MENU

    async def test_score_4_triggers_guidance_offer(self):
        result, _ = await self._run(4)
        assert result == CHECK_IN_GUIDANCE_OFFER

    async def test_score_3_triggers_guidance_offer(self):
        result, _ = await self._run(3)
        assert result == CHECK_IN_GUIDANCE_OFFER

    async def test_score_1_triggers_guidance_offer(self):
        result, _ = await self._run(1)
        assert result == CHECK_IN_GUIDANCE_OFFER

    async def test_low_mood_stores_entry_text(self):
        _, ctx = await self._run(3)
        assert ctx.user_data.get('entry_text') == 'I feel awful'

    async def test_high_mood_does_not_store_entry_text(self):
        _, ctx = await self._run(7)
        assert 'entry_text' not in ctx.user_data


# ---------------------------------------------------------------------------
# Crisis-resource delivery guarantee
#
# Resources must reach an acutely low-mood user unconditionally: not behind an
# opt-in, and not downstream of a DB or LLM call that can fail.
# ---------------------------------------------------------------------------

class TestCrisisResourceDelivery:
    def _sent(self, update) -> list:
        return [c.args[0] for c in update.message.reply_text.call_args_list]

    async def _run(self, mood_score: int, svc_error: Exception | None = None) -> MagicMock:
        ctx = _context({'name': 'Alice', 'mood_score': mood_score})
        update = _update('I feel awful')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            if svc_error is not None:
                mock_llm.extract_tags.side_effect = svc_error
            else:
                mock_llm.extract_tags.return_value = []
            mock_svc.get_stats.return_value = {'streak': 1, 'total': 1, 'avg_mood': mood_score}
            mock_llm.get_empathetic_response.return_value = 'Hang in there.'
            await handle_entry_text(update, ctx)
        return update

    async def test_score_2_receives_crisis_resources(self):
        update = await self._run(2)
        assert GUIDANCE_CRISIS_RESOURCES in self._sent(update)

    async def test_score_1_receives_crisis_resources(self):
        update = await self._run(1)
        assert GUIDANCE_CRISIS_RESOURCES in self._sent(update)

    async def test_score_3_does_not_receive_crisis_resources(self):
        update = await self._run(3)
        assert GUIDANCE_CRISIS_RESOURCES not in self._sent(update)

    async def test_delivered_even_when_the_check_in_fails(self):
        """The regression this fix exists for: a Mongo or LLM failure used to
        return ERROR_GENERIC and MAIN_MENU, skipping the crisis path entirely."""
        update = await self._run(1, svc_error=Exception('DB down'))
        assert GUIDANCE_CRISIS_RESOURCES in self._sent(update)

    async def test_delivered_before_anything_that_can_fail(self):
        update = await self._run(1)
        assert self._sent(update)[0] == GUIDANCE_CRISIS_RESOURCES

    def test_help_message_carries_crisis_resources(self):
        """/help is reachable mid-conversation, so it is the escape hatch that
        survives lost conversation state."""
        from messages.strings import HELP_MESSAGE
        assert 'iasp.info' in HELP_MESSAGE
        assert '116 123' in HELP_MESSAGE


# ---------------------------------------------------------------------------
# Consent notice
#
# Entry text leaves the product for a third-party API. That has to be disclosed
# before the first entry is written, and stay reachable afterwards.
# ---------------------------------------------------------------------------

class TestPrivacyNotice:
    async def test_new_user_sees_it_before_being_asked_anything(self):
        from messages.strings import PRIVACY_NOTICE
        update = _update('/start')
        with patch('bot.handlers.journal._user_svc') as mock_svc:
            mock_svc.get.return_value = None
            result = await start(update, _context())
        sent = [c.args[0] for c in update.message.reply_text.call_args_list]
        assert PRIVACY_NOTICE in sent
        assert result == ONBOARDING_NAME

    async def test_returning_user_is_not_shown_it_again(self):
        from messages.strings import PRIVACY_NOTICE
        update = _update('/start')
        with patch('bot.handlers.journal._user_svc') as mock_svc:
            mock_svc.get.return_value = {'name': 'Alice', 'onboarded': True}
            result = await start(update, _context())
        sent = [c.args[0] for c in update.message.reply_text.call_args_list]
        assert PRIVACY_NOTICE not in sent
        assert result == MAIN_MENU

    async def test_privacy_command_repeats_it(self):
        from bot.handlers.commands import privacy_command
        from messages.strings import PRIVACY_NOTICE
        update = _update('/privacy')
        await privacy_command(update, _context())
        assert update.message.reply_text.call_args.args[0] == PRIVACY_NOTICE

    def test_help_points_at_it(self):
        from messages.strings import HELP_MESSAGE
        assert '/privacy' in HELP_MESSAGE

    def test_welcome_makes_no_bare_privacy_claim(self):
        """The bot forwards entry text to a third-party API, so 'private
        anxiety journal' was an inaccurate opening line, not just a legal gap."""
        from messages.strings import ONBOARDING_WELCOME
        assert 'private' not in ONBOARDING_WELCOME.lower()


# ---------------------------------------------------------------------------
# Fail-closed handling of a missing mood score
# ---------------------------------------------------------------------------

class TestMissingMoodScore:
    async def test_entry_text_re_asks_instead_of_assuming(self):
        update = _update('I feel awful')
        with patch('bot.handlers.journal._journal_svc') as mock_svc, \
             patch('bot.handlers.journal._llm_svc') as mock_llm:
            result = await handle_entry_text(update, _context({'name': 'Alice'}))
        assert result == CHECK_IN_MOOD
        mock_svc.save_entry.assert_not_called()
        mock_llm.extract_tags.assert_not_called()

    async def test_entry_text_tells_the_user_it_was_not_saved(self):
        from messages.strings import MOOD_LOST
        update = _update('I feel awful')
        with patch('bot.handlers.journal._journal_svc'), \
             patch('bot.handlers.journal._llm_svc'):
            await handle_entry_text(update, _context({'name': 'Alice'}))
        assert update.message.reply_text.call_args.args[0] == MOOD_LOST

    async def test_guidance_offer_shows_crisis_resources(self):
        """This state is only reachable from a low-mood check-in, so a missing
        score means lost state rather than a well user."""
        from bot.keyboards import GUIDANCE_NO
        update = _update(GUIDANCE_NO)
        with patch('bot.handlers.journal._llm_svc'):
            result = await handle_guidance_offer(update, _context({'entry_text': 'rough'}))
        sent = [c.args[0] for c in update.message.reply_text.call_args_list]
        assert GUIDANCE_CRISIS_RESOURCES in sent
        assert result == MAIN_MENU


# ---------------------------------------------------------------------------
# Phase 6 — guidance offer handler
# ---------------------------------------------------------------------------

class TestHandleGuidanceOffer:
    def _ctx(self, mood_score: int = 3) -> MagicMock:
        return _context({'mood_score': mood_score, 'entry_text': 'feeling rough', 'name': 'Alice'})

    async def test_yes_returns_main_menu(self):
        from bot.keyboards import GUIDANCE_YES
        with patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_llm.get_psychological_guidance.return_value = 'Try deep breathing.'
            result = await handle_guidance_offer(_update(GUIDANCE_YES), self._ctx())
        assert result == MAIN_MENU

    async def test_yes_calls_llm(self):
        from bot.keyboards import GUIDANCE_YES
        with patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_llm.get_psychological_guidance.return_value = 'Try deep breathing.'
            await handle_guidance_offer(_update(GUIDANCE_YES), self._ctx())
        mock_llm.get_psychological_guidance.assert_called_once_with(3, 'feeling rough')

    async def test_no_returns_main_menu(self):
        from bot.keyboards import GUIDANCE_NO
        result = await handle_guidance_offer(_update(GUIDANCE_NO), self._ctx())
        assert result == MAIN_MENU

    async def test_no_skips_llm(self):
        from bot.keyboards import GUIDANCE_NO
        with patch('bot.handlers.journal._llm_svc') as mock_llm:
            await handle_guidance_offer(_update(GUIDANCE_NO), self._ctx())
        mock_llm.get_psychological_guidance.assert_not_called()

    async def test_any_other_text_treated_as_decline(self):
        result = await handle_guidance_offer(_update('random text'), self._ctx())
        assert result == MAIN_MENU

    async def test_crisis_resources_are_not_repeated_here(self):
        """handle_entry_text now delivers them unconditionally at mood <= 2,
        before this opt-in is ever offered. See TestCrisisResourceDelivery."""
        from bot.keyboards import GUIDANCE_YES
        update = _update(GUIDANCE_YES)
        with patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_llm.get_psychological_guidance.return_value = 'Try cold water.'
            await handle_guidance_offer(update, self._ctx(mood_score=2))
        sent = [c.args[0] for c in update.message.reply_text.call_args_list]
        assert GUIDANCE_CRISIS_RESOURCES not in sent

    async def test_score_3_does_not_append_crisis_resources(self):
        from bot.keyboards import GUIDANCE_YES
        update = _update(GUIDANCE_YES)
        with patch('bot.handlers.journal._llm_svc') as mock_llm:
            mock_llm.get_psychological_guidance.return_value = 'Try deep breathing.'
            await handle_guidance_offer(update, self._ctx(mood_score=3))
        sent_text = update.message.reply_text.call_args.args[0]
        assert GUIDANCE_CRISIS_RESOURCES not in sent_text


# ---------------------------------------------------------------------------
# Migration guard — v20+ requires coroutine callbacks
#
# A handler that is accidentally left synchronous still registers fine and only
# fails when a user reaches it, so assert the shape here instead.
# ---------------------------------------------------------------------------

class TestHandlersAreCoroutines:
    def test_every_registered_handler_is_async(self):
        import inspect
        from bot.handlers import commands, journal

        callbacks = [
            journal.start,
            journal.handle_name,
            journal.handle_timezone,
            journal.handle_timezone_location,
            journal.handle_reminder_time,
            journal.handle_main_menu,
            journal.handle_mood,
            journal.handle_entry_text,
            journal.show_history,
            journal.show_stats,
            journal.show_weekly_summary,
            journal.handle_guidance_offer,
            journal.cancel,
            commands.help_command,
            commands.privacy_command,
        ]
        not_async = [c.__name__ for c in callbacks if not inspect.iscoroutinefunction(c)]
        assert not_async == []

    def test_register_accepts_an_application(self):
        """`dispatcher.add_handler` is gone in v20+; registration goes through
        Application. Passing a mock proves the call shape, not the wiring."""
        from bot.handlers import commands, journal

        app = MagicMock()
        journal.register(app)
        commands.register(app)
        assert app.add_handler.call_count == 3
