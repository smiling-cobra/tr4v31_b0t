from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from messages.strings import HELP_MESSAGE, PRIVACY_NOTICE


def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')


def privacy_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(PRIVACY_NOTICE, parse_mode='Markdown')


def register(dispatcher) -> None:
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('privacy', privacy_command))
