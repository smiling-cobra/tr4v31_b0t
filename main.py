import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from handlers import GroupMessageHandler, UserDialogueHelper

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG (you can use INFO, WARNING, ERROR, etc.)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')
    pass

def help(update: Update, context: CallbackContext):
    update.message.reply_text("Here's how you can use this bot: ...")
    pass
    
def setup_error_handler(dispatcher):
    # Errors
    dispatcher.add_error_handler(error)

def main() -> None:
    print('Starting bot...')

    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher
    
    setup_error_handler(dispatcher)
    
    conversation_handler = UserDialogueHelper(dispatcher)
    conversation_handler.setup()
    
    group_message_handler = GroupMessageHandler(dispatcher)
    group_message_handler.setup()
    
    dispatcher.add_handler(CommandHandler('help', help))

    # Start polling the bot for updates
    print('Polling...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()