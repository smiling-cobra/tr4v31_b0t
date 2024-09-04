from commands import Command
from telegram import Update
from telegram.ext import CallbackContext
from common import get_lobby_keyboard
from messages import create_following_question_message, DEFAULT_USER_NAME

DESTINATION, LOBBY = range(2)

class BackCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        update.message.reply_text(
            create_following_question_message(user_name),
            reply_markup=get_lobby_keyboard()
        )
        return LOBBY
