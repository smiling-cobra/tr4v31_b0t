from commands import Command
from telegram import Update
from telegram.ext import CallbackContext
from common import get_lobby_keyboard

class BackCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text("What else can I help you with? 👀", reply_markup=get_lobby_keyboard())
        return LOBBY