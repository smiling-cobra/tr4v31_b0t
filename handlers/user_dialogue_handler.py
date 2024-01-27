import os
import requests
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
    Phrases,
    VenuePhotoRetriever
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler
)
from services import OpenAIHelper
from messages import (
    NO_CITY_FOUND_MESSAGE,
    DEFAULT_USER_NAME,
    create_initial_greeting_message,
    create_wrong_input_message,
    create_farewell_message
)

google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')
geocoding_api_url = os.environ.get('GEOCODING_API_URL')

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
foursquare_auth_key = os.environ.get('FOURSQUARE_API_KEY')

DESTINATION, LOBBY = range(2)
CITY_REQUEST_ERROR_TEXT = 'No city was found! Status: ZERO_RESULTS'

TOURIST_ATTRACTIONS = '🗽 Sites'
WEATHER_FORECAST = '☀️ Weather'
AFFORDABLE_EATS = '🥗 Eats'
LOCAL_PHRASES = '🗣 Phrases'
FIVE_FACTS = '🎲 Stories'
TRAVEL_TIPS = '🎯 Tips'
HELP = '❓ Help'
BACK = '🔙 Back'

openai_helper = OpenAIHelper()

venue_photo_retriever = VenuePhotoRetriever(
    client_id, client_secret,
    foursquare_auth_key
)

user_choice_to_command = {
    TOURIST_ATTRACTIONS: Landmarks(get_city_name, get_option_keyboard),
    WEATHER_FORECAST: Weather(get_city_name, get_option_keyboard),
    AFFORDABLE_EATS: Restauraunts(
        venue_photo_retriever,
        get_city_name,
        get_option_keyboard
    ),
    LOCAL_PHRASES: Phrases(),
    TRAVEL_TIPS: Tips(openai_helper, get_city_name),
    FIVE_FACTS: Stories(openai_helper, get_city_name),
    HELP: HelpCommand(),
    BACK: BackCommand()
}


def fetch_city_data(
        city_name: str,
        google_api_key: str,
        geocoding_api_url: str,
        context: CallbackContext
):

    req_params = {
        "address": city_name,
        "key": google_api_key
    }

    response = requests.get(geocoding_api_url, params=req_params)

    try:
        data = response.json()
    except ValueError as e:
        return f"Error parsing JSON: {e}"

    response_status = data.get('status')

    if response_status == 'OK':
        city_data = data.get('results')
        print('City data: ', city_data)
        context.user_data['city_data'] = city_data
        return city_data
    else:
        return f"No city was found! Status: {response_status}"


class UserDialogueHelper:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def handle_initial_user_input(
        self,
        update: Update,
        context: CallbackContext
    ):
        user_input = update.message.text.capitalize()
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME

        city_data = fetch_city_data(
            user_input,
            google_map_api_key,
            geocoding_api_url,
            context
        )

        if city_data == CITY_REQUEST_ERROR_TEXT:
            update.message.reply_text(NO_CITY_FOUND_MESSAGE)
        else:
            update.message.reply_text(
                create_initial_greeting_message(user_name, user_input),
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
