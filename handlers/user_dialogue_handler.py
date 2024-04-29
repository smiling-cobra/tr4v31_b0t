import os
from common import get_lobby_keyboard, get_city_name, get_option_keyboard
from messages import WELCOME_MESSAGE_CONCISE
from telegram import Update, ReplyKeyboardRemove
from commands import (
    Landmarks,
    Restauraunts,
    Weather,
    Stories,
    BackCommand,
    HelpCommand,
    Tips,
    Events,
    VenuePhotoRetriever
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler
)
from services import OpenAIHelper, LoggingService
from messages import (
    NO_CITY_FOUND_MESSAGE,
    DEFAULT_USER_NAME,
    create_initial_greeting_message,
    create_wrong_input_message,
    create_farewell_message
)

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
foursquare_auth_key = os.environ.get('FOURSQUARE_API_KEY')

DESTINATION, LOBBY = range(2)

openai_helper = OpenAIHelper()
logger = LoggingService()

venue_photo_retriever = VenuePhotoRetriever(
    client_id, client_secret,
    foursquare_auth_key
)

TOURIST_ATTRACTIONS = '🗽 Sites'
WEATHER_FORECAST = '☀️ Weather'
AFFORDABLE_EATS = '🥗 Eats'
EVENTS = '⭐ Events'
STORIES = '🎲 Stories'
TRAVEL_TIPS = '🎯 Tips'
HELP = '❓ Help'
BACK = '🔙 Back'

user_choice_to_command = {
    TOURIST_ATTRACTIONS: Landmarks(
        get_city_name,
        get_option_keyboard
    ),
    WEATHER_FORECAST: Weather(
        get_city_name,
        get_option_keyboard,
        logger
    ),
    AFFORDABLE_EATS: Restauraunts(
        venue_photo_retriever,
        get_city_name,
        get_option_keyboard
    ),
    EVENTS: Events(
        get_city_name,
        get_option_keyboard,
        logger
    ),
    TRAVEL_TIPS: Tips(
        openai_helper,
        get_city_name,
        get_option_keyboard
    ),
    STORIES: Stories(
        openai_helper,
        get_city_name,
        get_option_keyboard
    ),
    HELP: HelpCommand(),
    BACK: BackCommand()
}


class UserDialogueHelper:
    def __init__(self, dispatcher, city_data_service):
        self.dispatcher = dispatcher
        self.city_data_service = city_data_service

    def handle_initial_user_input(
        self,
        update: Update,
        context: CallbackContext
    ):
        user_input = update.message.text
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME

        city_data = self.city_data_service.fetch_city_data(user_input)

        if not city_data:
            update.message.reply_text(
                NO_CITY_FOUND_MESSAGE.format(user_name),
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Save city data in context
        context.user_data['city_data'] = city_data
                
        destination = city_data[0].get('formatted_address')

        update.message.reply_text(
            create_initial_greeting_message(user_name, destination),
            reply_markup=get_lobby_keyboard()
        )

        return LOBBY

    def handle_lobby_choice(self, update: Update, context: CallbackContext):
        user_choice = update.message.text
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        command = user_choice_to_command.get(user_choice)
        
        if command:
            command.execute(update, context)
        else:
            update.message.reply_text(create_wrong_input_message(user_name))

    def start(self, update: Update, context: CallbackContext):
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        welcome_message = WELCOME_MESSAGE_CONCISE.format(user_name)
        update.message.reply_text(welcome_message)
        return DESTINATION

    def cancel(self, update: Update, context: CallbackContext):
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME

        update.message.reply_text(
            create_farewell_message(user_name),
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    def setup(self):
        # Create the ConversationHandler to handle
        # the onboarding process and lobby choices

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                DESTINATION: [
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        self.handle_initial_user_input
                    )
                ],
                LOBBY: [
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        self.handle_lobby_choice
                    )
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        # Add the ConversationHandler to the dispatcher
        self.dispatcher.add_handler(conv_handler)
