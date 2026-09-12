"""Tests for the global error handler.

Without one, an exception escaping a handler leaves the user with no reply at
all — waiting on a bot that has silently dropped their message.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from telegram import Update

from bot.handlers.errors import handle_error
from messages.strings import ERROR_GENERIC


def _context(error: Exception) -> MagicMock:
    ctx = MagicMock()
    ctx.error = error
    return ctx


def _update() -> MagicMock:
    update = MagicMock(spec=Update)
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


class TestErrorHandler:
    async def test_tells_the_user_something_went_wrong(self):
        update = _update()
        await handle_error(update, _context(RuntimeError('boom')))
        assert update.effective_message.reply_text.call_args.args[0] == ERROR_GENERIC

    async def test_reattaches_the_main_menu_keyboard(self):
        """The user is re-anchored: whatever state was lost, their next tap works."""
        update = _update()
        await handle_error(update, _context(RuntimeError('boom')))
        assert update.effective_message.reply_text.call_args.kwargs['reply_markup'] is not None

    async def test_ignores_errors_that_have_no_update(self):
        # A failure inside a scheduled job arrives with no update to answer.
        await handle_error(None, _context(RuntimeError('boom')))

    async def test_ignores_a_non_update_object(self):
        await handle_error(object(), _context(RuntimeError('boom')))

    async def test_survives_a_failure_while_reporting_the_failure(self):
        update = _update()
        update.effective_message.reply_text = AsyncMock(side_effect=Exception('telegram down'))
        await handle_error(update, _context(RuntimeError('boom')))

    async def test_handles_an_update_with_no_message(self):
        update = MagicMock(spec=Update)
        update.effective_message = None
        await handle_error(update, _context(RuntimeError('boom')))
