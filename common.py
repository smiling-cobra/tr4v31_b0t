from telegram import KeyboardButton, ReplyKeyboardMarkup


TOURIST_ATTRACTIONS = '🗽 Sites'
WEATHER_FORECAST = '☀️ Weather'
AFFORDABLE_EATS = '🥗 Eats'
LOCAL_PHRASES = '🗣 Phrases'
TRAVEL_TIPS = '🎯 Tips'
FIVE_FACTS = '🎲 Facts'
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