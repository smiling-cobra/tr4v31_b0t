import functools
import logging

from bot.keyboards import get_main_menu_keyboard
from bot.handlers.journal.states import MAIN_MENU
from messages.strings import ERROR_GENERIC

logger = logging.getLogger(__name__)


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
