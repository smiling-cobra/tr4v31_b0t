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

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG (you can use INFO, WARNING, ERROR, etc.)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
weather_api_key = os.environ.get('OPEN_WEATHER_API_KEY')
openai.api_key = os.environ.get('OPEN_AI_KEY')
google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')

class Command(ABC):
    @abstractmethod
    def execute(self, update: Update, context: CallbackContext) -> None:
        pass

class TouristAttractionsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        # landmarks = self.get_landmarks(city_name)
        
        places = self.get_places(city_name)
        context.user_data['landmarks'] = places
        update.message.reply_text(f"Here are some popular tourist attractions in {city_name}:", reply_markup=self.get_landmark_keyboard())
        
        self.post_landmarks(update, context, places)
    
    def get_places(self, city_name: str) -> list:
        GOOGLE_PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

        params = {
            'query': f"landmarks in {city_name}",
            'inputtype': 'textquery',
            'fields': 'photos,place_id,geometry',
            'key': google_map_api_key
        }

        response = requests.get(GOOGLE_PLACES_API_URL, params=params)
        
        try:
            data = response.json()
        except ValueError as e:
            return []
            print(f"Error parsing JSON: {e}")
        
        response_status = data.get('status')
        
        if response_status == 'OK':
            places = data.get('results', [])
            places_list = self.compose_places_list(places)
            # Limit the number of places to 5 for now
            places_list_limited = places_list[:5]
            return places_list_limited
        else:
            return f"No places were found! Status: {response_status}"
        
    def compose_places_list(self, places: list) -> None:
        GOOGLE_PHOTO_API_URL = "https://maps.googleapis.com/maps/api/place/photo"
        landmarks_info = []
        
        for place in places:
            landmark = {}
            photos = place.get('photos', [])
            if photos:
                photo_ref = photos[0].get('photo_reference')
                if photo_ref:
                    photo_params = {
                        'maxwidth': 400,
                        'photoreference': photo_ref,
                        'key': google_map_api_key
                    }
                    
                    try:
                        photo_url = requests.get(GOOGLE_PHOTO_API_URL, params=photo_params).url
                        landmark['photo'] = photo_url
                    except ValueError as e:
                        return []
                        print(f"Error parsing JSON: {e}")
            
            landmark['name'] = place.get('name')
            landmark['formatted_address'] = place.get('formatted_address')
            
            landmarks_info.append(landmark)
            
        return landmarks_info
    
    def format_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'
    
    def get_landmark_keyboard(self) -> InlineKeyboardMarkup:
        # Return the InlineKeyboardMarkup with the "Back to Lobby" button
        back_to_lobby_button = KeyboardButton("🔙 Back")
        more_landmarks_button = KeyboardButton("🗽 Show me more landmarks!")
        keyboard = [[back_to_lobby_button], [more_landmarks_button]]
        return ReplyKeyboardMarkup(keyboard)
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name
    
    # def get_landmarks(self, city_name: str) -> list:
    #     version = date.today().strftime("%Y%m%d")

    #     params = {
    #         'client_id': client_id,
    #         'client_secret': client_secret,
    #         'v': version,
    #         'near': city_name,
    #         'query': 'landmarks',
    #         'limit': 5,
    #         'fields' :'name,location'
    #     }

    #     headers = {
    #         "accept": "application/json",
    #         "Authorization": "fsq3EspygHQ4vVEBDjCoZ/j/Jz23u08mtTLHp66gpA0idio="
    #     }

    #     response = requests.get(base_url, params=params, headers=headers)

    #     if response.status_code == 200:
    #         data_list = response.json()
    #         return data_list
    #     else:
    #         return []

    def post_landmarks(self, update: Update, context: CallbackContext, landmarks: list) -> None:
        for landmark in landmarks:
            landmark_name = landmark.get('name')                
            landmark_location = landmark.get('formatted_address')
            landmark_photo = landmark.get('photo')
            
            if landmark_photo:
                update.message.reply_photo(photo=landmark_photo)
                
            landmark_location_as_link = self.format_address_as_link(landmark_location)
            message_text = f"{landmark_name}\n{landmark_location_as_link}"
            update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
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
        back_to_lobby_button = KeyboardButton("🔙 Back")
        more_restauraunts_button = KeyboardButton(f"🥗 Show me more restaurants in {city_name}!")
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
    