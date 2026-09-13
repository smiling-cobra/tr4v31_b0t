from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.handlers.journal.states import CHECK_IN_MOOD, MAIN_MENU
from bot.handlers.journal.views import show_history, show_stats, show_weekly_summary
from bot.keyboards import CHECK_IN, HELP, HISTORY, STATS, WEEKLY_SUMMARY, get_mood_keyboard
from messages.strings import CANCEL_MESSAGE, CHECK_IN_MOOD_PROMPT, HELP_MESSAGE


def _name(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get('name', 'there')


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    name = _name(context)

    if choice == CHECK_IN:
        await update.message.reply_text(
            CHECK_IN_MOOD_PROMPT.format(name=name),
            reply_markup=get_mood_keyboard()
        )
        return CHECK_IN_MOOD

    if choice == HISTORY:
        return await show_history(update, context)

    if choice == STATS:
        return await show_stats(update, context)

    if choice == WEEKLY_SUMMARY:
        return await show_weekly_summary(update, context)

    if choice == HELP:
        await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')
        return MAIN_MENU

    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        CANCEL_MESSAGE.format(name=_name(context)),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END
