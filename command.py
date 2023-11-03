import os
import html
import openai
import logging
import requests
from datetime import date
from abc import ABC, abstractmethod
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from common import get_lobby_keyboard
from commands import Command

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG (you can use INFO, WARNING, ERROR, etc.)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
foursquare_auth_key = os.environ.get('FOURSQUARE_API_KEY')
weather_api_key = os.environ.get('OPEN_WEATHER_API_KEY')
openai.api_key = os.environ.get('OPEN_AI_KEY')
google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')

    
class AffordableEatsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        restaurants = self.get_restauraunts(city_name)
        
        context.user_data['affordable_eats'] = restaurants
        update.message.reply_text(f"Here are some affordable places to eat in {city_name}, sorted by rating:", reply_markup=self.get_affordable_eats_keyboard(context))
        
        self.post_restauraunts(update, context, restaurants)
    
    def format_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'
    
    def get_affordable_eats_keyboard(self, context: CallbackContext) -> InlineKeyboardMarkup:
        city_name = self.get_city_name(context)
        return ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")], [KeyboardButton(f"🥗 Show me more restaurants in {city_name}!")]])
    
    def get_venue_photos(self, venue_id: str) -> str:
        url = f'https://api.foursquare.com/v3/places/{venue_id}/photos'
        params = {
            'client_id': client_id,
            'client_secret': client_secret,
        }
        
        headers = {
            "accept": "application/json",
            "Authorization": foursquare_auth_key
        }

        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            photos = response.json()
            if photos:
                venue_photo_url = f"{photos[0].get('prefix')}300x300{photos[0].get('suffix')}"
                return venue_photo_url
        else:
            return []

    
    def get_restauraunts(self, city_name: str) -> list:
        # https://location.foursquare.com/developer/reference/response-fields
        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'near': city_name,
            'query': 'restaurants',
            'limit': 10,
            'fields' :'name,location,fsq_id,distance,link',  
            'sort': 'rating'
        }

        headers = {
            "accept": "application/json",
            "Authorization": foursquare_auth_key
        }

        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            venues = data.get('results')
            for venue in venues:
                venue_id = venue.get('fsq_id')
                venue['photo'] = self.get_venue_photos(venue_id)
            return venues
        else:
            return []
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name
    
    def post_restauraunts(self, update: Update, context: CallbackContext, restaurants: list) -> None:
        for restaurant in restaurants:
            restaurant_name = restaurant.get('name')
            restaurant_location = restaurant.get('location').get('formatted_address')
            restaurant_photo = restaurant.get('photo')
            
            if restaurant_photo:
                update.message.reply_photo(photo=restaurant_photo)
            
            restaurant_location_as_link = self.format_address_as_link(restaurant_location)
            message_text = f"{restaurant_name}\n{restaurant_location_as_link}"
            update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

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
        city_name = self.get_city_name(context)
        update.message.reply_text(f"Here are some facts about {city_name}:")
        city_facts = self.get_facts(city_name)
        print('city', city_facts)
    
    def get_facts(self, city_name: str) -> str:
        prompt = f"Tell me some interesting facts about {city_name}"
        
        try:
            response = openai.Completion.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt
            )
        except Exception as e:
            print(f"An error occured: {e}")
        
        facts = response.choices[0].text.strip()
        return facts
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name

class WeatherForecastCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_coordinates = self.get_city_coordinates(context)
        weather_now = self.get_weather_forecast(city_coordinates)
        weather_desc = weather_now.get('daily')[0].get('summary')
        update.message.reply_text(f'Here is the weather forecast for your destination: {weather_desc}', reply_markup=self.get_weather_keyboard())
        pass

    def get_city_coordinates(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        lat = city_data.get('geometry').get('location').get('lat')
        lng = city_data.get('geometry').get('location').get('lng')
        return {'lat': lat, 'lng': lng}
    
    def get_weather_forecast(self, city_coordinates: dict) -> list:
        lat = city_coordinates.get("lat")
        lon = city_coordinates.get("lng")
        appid = '23f15497c341cb62b6878982f298236f'
        weather_url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={appid}'

        response = requests.get(weather_url)

        if response.status_code == 200:
            weather_data = response.json()
            return weather_data
        else:
            return []
    
    def get_weather_keyboard(self) -> InlineKeyboardMarkup:
        # Return the InlineKeyboardMarkup with the "Back to Lobby" button
        back_to_lobby_button = KeyboardButton("🔙 Back")
        more_landmarks_button = KeyboardButton("☀️ Tell me more about current weather!")
        keyboard = [[back_to_lobby_button], [more_landmarks_button]]
        return ReplyKeyboardMarkup(keyboard)

class HelpCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide help or instructions
        update.message.reply_text("How can I assist you?")
        pass


class BackCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text("What else can I help you with? 👀", reply_markup=get_lobby_keyboard())
        return LOBBY
    