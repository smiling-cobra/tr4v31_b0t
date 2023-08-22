import os
import html
import logging
import requests
from datetime import date
from abc import ABC, abstractmethod
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# # Configure the logging settings
# logging.basicConfig(
#     level=logging.DEBUG,  # Set the logging level to DEBUG (you can use INFO, WARNING, ERROR, etc.)
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')

class Command(ABC):
    @abstractmethod
    def execute(self, update: Update, context: CallbackContext) -> None:
        pass

class TouristAttractionsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        landmarks = self.get_landmarks(city_name)
        context.user_data['landmarks'] = landmarks['results']
        update.message.reply_text(f"Here are some popular tourist attractions in {city_name}:", reply_markup=self.get_landmark_keyboard())
        self.post_landmarks(update, context, landmarks)
    
    def format_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'
    
    def get_landmark_keyboard(self) -> InlineKeyboardMarkup:
        # Return the InlineKeyboardMarkup with the "Back to Lobby" button
        back_to_lobby_button = KeyboardButton("Back")
        more_landmarks_button = KeyboardButton("Show me more landmarks!")
        keyboard = [[back_to_lobby_button], [more_landmarks_button]]
        return ReplyKeyboardMarkup(keyboard)
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name
    
    def get_landmarks(self, city_name: str) -> list:
        version = date.today().strftime("%Y%m%d")

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'v': version,
            'near': city_name,
            'query': 'landmarks',
            'limit': 5,
            'fields' :'name,location'
        }

        headers = {
            "accept": "application/json",
            "Authorization": "fsq3EspygHQ4vVEBDjCoZ/j/Jz23u08mtTLHp66gpA0idio="
        }

        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data_list = response.json()
            return data_list
        else:
            return []

    def post_landmarks(self, update: Update, context: CallbackContext, landmarks: list) -> None:
        city_landmarks = landmarks.get('results')
        for landmark in city_landmarks:
            landmark_name = landmark.get('name')
            landmark_location = landmark.get('location').get('formatted_address')
            landmark_location_as_link = self.format_address_as_link(landmark_location)
            message_text = f"{landmark_name}\n{landmark_location_as_link}"
            update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        pass
    

class AffordableEatsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        restaurants = self.get_restauraunts(city_name)
        context.user_data['affordable_eats'] = restaurants['results']
        update.message.reply_text(f"Here are some affordable places to eat in {city_name}, sorted by rating:", reply_markup=self.get_affordable_eats_keyboard(context))
        self.post_restauraunts(update, context, restaurants)
    
    def format_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'
    
    def get_affordable_eats_keyboard(self, context: CallbackContext) -> InlineKeyboardMarkup:
        city_name = self.get_city_name(context)
        back_to_lobby_button = KeyboardButton("Back")
        more_restauraunts_button = KeyboardButton(f"Show me more restaurants in {city_name}!")
        keyboard = [[back_to_lobby_button], [more_restauraunts_button]]
        return ReplyKeyboardMarkup(keyboard)
    
    def get_restauraunts(self, city_name: str) -> list:
        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'near': city_name,
            'query': 'restaurants',
            'limit': 10,
            'fields' :'name,location',
            'sort': 'rating'
        }

        headers = {
            "accept": "application/json",
            "Authorization": "fsq3EspygHQ4vVEBDjCoZ/j/Jz23u08mtTLHp66gpA0idio="
        }

        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data_list = response.json()
            return data_list
        else:
            return []
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name
    
    def post_restauraunts(self, update: Update, context: CallbackContext, restaurants: list) -> None:
        city_restaurants = restaurants.get('results')
        for restaurant in city_restaurants:
            restaurant_name = restaurant.get('name')
            restaurant_location = restaurant.get('location').get('formatted_address')
            restaurant_location_as_link = self.format_address_as_link(restaurant_location)
            message_text = f"{restaurant_name}\n{restaurant_location_as_link}"
            update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        pass

class LocalPhrasesCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide local phrases
        update.message.reply_text("Here are some useful local phrases:")
        pass

class TravelTipsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide travel tips
        update.message.reply_text("Here are some travel tips for your destination:")
        pass

class FiveFactsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide help or instructions
        update.message.reply_text("Here are some facts about your destination:")
        pass

class WeatherForecastCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide weather forecast
        update.message.reply_text("Here's the weather forecast for your destination:")
        pass

class HelpCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide help or instructions
        update.message.reply_text("How can I assist you?")
        pass
    