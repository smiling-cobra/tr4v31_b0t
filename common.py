from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext


TOURIST_ATTRACTIONS = '🗽 Sites'
WEATHER_FORECAST = '☀️ Weather'
AFFORDABLE_EATS = '🥗 Eats'
LOCAL_PHRASES = '🗣 Phrases'
TRAVEL_TIPS = '🎯 Tips'
FIVE_FACTS = '🎲 Stories'
HELP = '❓ Help'
BACK = '🔙 Back'


def get_lobby_keyboard():
    options = [
        [TOURIST_ATTRACTIONS, WEATHER_FORECAST, AFFORDABLE_EATS],
        [LOCAL_PHRASES, TRAVEL_TIPS, FIVE_FACTS],
        [HELP, BACK]
    ]

    keyboard = [[KeyboardButton(option) for option in row] for row in options]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_city_name(context: CallbackContext) -> str:
    city_data = context.user_data.get('city_data')[0]
    address_components = city_data.get('address_components')[0]
    city_name = address_components.get('long_name')
    return city_name


def get_option_keyboard(message: str) -> InlineKeyboardMarkup:
    back_button = KeyboardButton("🔙 Back")
    show_more_button = KeyboardButton(message)
    keyboard = [[back_button], [show_more_button]]
    return ReplyKeyboardMarkup(keyboard)