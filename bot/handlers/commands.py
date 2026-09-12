from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from messages.strings import HELP_MESSAGE, PRIVACY_NOTICE


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(PRIVACY_NOTICE, parse_mode='Markdown')


def register(application: Application) -> None:
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('privacy', privacy_command))
