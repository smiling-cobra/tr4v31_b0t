import os
import logging
import requests
from common import get_lobby_keyboard
from messages import WELCOME_MESSAGE_LONG, WELCOME_MESSAGE_CONCISE
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from commands import Landmarks, Restauraunts, Weather, Stories, BackCommand, HelpCommand, Tips, Phrases, VenuePhotoRetriever
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from services import OpenAIHelper


# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG (you can use INFO, WARNING, ERROR, etc.)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')
google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')
geocoding_api_url = os.environ.get('GEOCODING_API_URL')

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
foursquare_auth_key = os.environ.get('FOURSQUARE_API_KEY')

TOURIST_ATTRACTIONS = '🗽 Sites'
WEATHER_FORECAST = '☀️ Weather'
AFFORDABLE_EATS = '🥗 Eats'
LOCAL_PHRASES = '🗣 Phrases'
FIVE_FACTS = '🎲 Stories'
TRAVEL_TIPS = '🎯 Tips'
HELP = '❓ Help'
BACK = '🔙 Back'

CITY_REQUEST_ERROR_TEXT = 'No city was found! Status: ZERO_RESULTS'

# Define states for the conversation
DESTINATION, LOBBY = range(2)

openai_helper = OpenAIHelper()
venue_photo_retriever = VenuePhotoRetriever(client_id, client_secret, foursquare_auth_key)

user_choice_to_command = {
    TOURIST_ATTRACTIONS: Landmarks(),
    WEATHER_FORECAST: Weather(),
    AFFORDABLE_EATS: Restauraunts(venue_photo_retriever),
    LOCAL_PHRASES: Phrases(),
    TRAVEL_TIPS: Tips(),
    FIVE_FACTS: Stories(openai_helper),
    HELP: HelpCommand(),
    BACK: BackCommand()
}


def fetch_city_data(city_name: str, google_api_key: str, geocoding_api_url: str, context: CallbackContext):
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
        context.user_data['city_data'] = city_data
        return city_data
    else:
        return f"No city was found! Status: {response_status}"


def handle_initial_user_input(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_name = update.message.chat.first_name
    city_data = fetch_city_data(user_input, google_map_api_key, geocoding_api_url, context)

    if city_data == CITY_REQUEST_ERROR_TEXT:
        update.message.reply_text("🤷‍♂️ Excusez-moi but no city was found... Try again!")
    else:
        update.message.reply_text(
            f"🔥 Awesome, {user_name}! You're traveling to {user_input}! Here's what I can offer ⤵️",
            reply_markup=get_lobby_keyboard()
        )
        return LOBBY


def group_message_handler(update: Update, context: CallbackContext):
    # Extract the message and chat details
    message = update.message
    chat = message.chat
    text = message.text

    # Check if the bot is mentioned in the group chat
    if f"@{context.bot.username}" in text:
        # Process the message following the mention
        response_text = process_group_message(text, chat.id)
        # Send a reply to the group
        message.reply_text(response_text)
    else:
        # Handle other group messages (if needed)
        # For instance, you can log the message or perform some actions
        # Note: Be mindful of privacy and group rules
        pass

def process_group_message(text, chat_id):
    # Custom logic to process the message
    # For example, stripping the bot's mention and generating a response
    clean_text = text.replace(f"@{context.bot.username}", "").strip()
    response = f"Received in chat {chat_id}: {clean_text}"
    return response


def handle_lobby_choice(update: Update, context: CallbackContext):
    user_choice = update.message.text
    user_name = update.message.chat.first_name
    command = user_choice_to_command.get(user_choice)

    if command:
        command.execute(update, context)
    else:
        update.message.reply_text(f"🤷‍♂️ You've probably made a wrong input, {user_name}. Give it another try!")


def start(update: Update, context: CallbackContext):
    user_name = update.message.chat.first_name or 'Traveler'
    welcome_message = WELCOME_MESSAGE_CONCISE.format(user_name)
    update.message.reply_text(welcome_message)
    return DESTINATION


def cancel(update: Update, context: CallbackContext):
    user_name = update.message.chat.first_name
    update.message.reply_text(f"👋 Have a nice trip, {user_name}! Feel free to reach out again anytime!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')
    pass

def help(update: Update, context: CallbackContext):
    update.message.reply_text("Here's how you can use this bot: ...")
    pass

def setup_conversation_handler(dispatcher):
    # Create the ConversationHandler to handle the onboarding process and lobby choices
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            DESTINATION: [MessageHandler(Filters.text & ~Filters.command, handle_initial_user_input)],
            LOBBY: [MessageHandler(Filters.text & ~Filters.command, handle_lobby_choice)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    # Add the ConversationHandler to the dispatcher
    dispatcher.add_handler(conv_handler)

def setup_group_message_handler(dispatcher):
    # Add group chat handler
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, group_message_handler))
    
def setup_error_handler(dispatcher):
    # Errors
    dispatcher.add_error_handler(error)

def main() -> None:
    print('Starting bot...')

    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher

    setup_conversation_handler(dispatcher)
    setup_group_message_handler(dispatcher)
    setup_error_handler(dispatcher)
    
    dispatcher.add_handler(CommandHandler('help', help))

    # Start polling the bot for updates
    print('Polling...')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()