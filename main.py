import os
import requests
from common import get_lobby_keyboard
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from messages import WELCOME_MESSAGE_LONG, WELCOME_MESSAGE_CONCISE
from command import TouristAttractionsCommand, WeatherForecastCommand, AffordableEatsCommand, LocalPhrasesCommand, TravelTipsCommand, FiveFactsCommand, HelpCommand, BackCommand

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')
google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')
geocoding_api_url = os.environ.get('GEOCODING_API_URL')

TOURIST_ATTRACTIONS = '🗽 Sites'
WEATHER_FORECAST = '☀️ Weather'
AFFORDABLE_EATS = '🥗 Eats'
LOCAL_PHRASES = '🗣 Phrases'
TRAVEL_TIPS = '🎯 Tips'
FIVE_FACTS = '🎲 Facts'
HELP = '❓ Help'
BACK = '🔙 Back'

CITY_REQUEST_ERROR_TEXT = 'No city was found! Status: ZERO_RESULTS'

# Define states for the conversation
DESTINATION, LOBBY = range(2)


user_choice_to_command = {
    TOURIST_ATTRACTIONS: TouristAttractionsCommand(),
    WEATHER_FORECAST: WeatherForecastCommand(),
    AFFORDABLE_EATS: AffordableEatsCommand(),
    LOCAL_PHRASES: LocalPhrasesCommand(),
    TRAVEL_TIPS: TravelTipsCommand(),
    FIVE_FACTS: FiveFactsCommand(),
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


def handle_message(update: Update, context: CallbackContext):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User({update.message.chat.id}) in {message_type} : "{text}"')
    
    # This block is to handle cases when you want to mention [travel_bot] directly in group chat.
    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)
    
    print('Bot:', response)
    update.message.reply_text(response)


def handle_lobby_choice(update: Update, context: CallbackContext):
    user_choice = update.message.text
    user_name = update.message.chat.first_name
    command = user_choice_to_command.get(user_choice)

    if command:
        command.execute(update, context)
    else:
        update.message.reply_text(f"🤷‍♂️ You've probably made a wrong input, {user_name}. Give it another try!")


def start(update: Update, context: CallbackContext):
    user_name = update.message.chat.first_name
    welcome_message = WELCOME_MESSAGE_CONCISE.format(user_name)
    update.message.reply_text(welcome_message)
    return DESTINATION


def cancel(update: Update, context: CallbackContext):
    user_name = update.message.chat.first_name
    update.message.reply_text(f"👋 Have a nice trip, {user_name}! Feel free to reach out again anytime!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')


def main() -> None:
    print('Starting bot...')

    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher

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

    # Errors
    dispatcher.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()