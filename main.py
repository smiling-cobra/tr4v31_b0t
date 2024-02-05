import os
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from handlers import GroupMessageHandler, UserDialogueHelper
from messages import HELP_WELCOME_MESSAGE
from services import CityDataService, LoggingService

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')
geocoding_api_url = os.environ.get('GEOCODING_API_URL')
google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')


def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')
    pass


def help(update: Update, context: CallbackContext):
    update.message.reply_text(HELP_WELCOME_MESSAGE)
    pass


def setup_error_handler(dispatcher):
    # Errors
    dispatcher.add_error_handler(error)


city_data_service = CityDataService(
    requests,
    google_map_api_key,
    geocoding_api_url,
    LoggingService()
)


def main() -> None:
    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher
    
    logger = LoggingService()
    logger.log('info', 'Application start')

    setup_error_handler(dispatcher)

    conversation_handler = UserDialogueHelper(
        dispatcher,
        city_data_service
    )
    conversation_handler.setup()

    group_message_handler = GroupMessageHandler(dispatcher)
    group_message_handler.setup()

    dispatcher.add_handler(CommandHandler('help', help))

    # Start polling the bot for updates
    logger.log('info', 'Polling...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
