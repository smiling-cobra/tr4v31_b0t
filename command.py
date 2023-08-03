import os
import logging
import requests
from datetime import date
from abc import ABC, abstractmethod
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
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
        tourist_attractions = self.get_tourist_attractions(city_name)
        print(tourist_attractions)
        update.message.reply_text(f"Here are some popular tourist attractions in {city_name}:")
        pass
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name
    
    def get_tourist_attractions(self, city_name: str) -> list:
        # Your code to get tourist attractions
        version = date.today().strftime("%Y%m%d")

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'v': version,
            'near': city_name,
            'query': 'tourist_attraction',
            'limit': 5
        }

        # Usage of the V2 Places API has been deprecated for new Projects
        # https://docs.foursquare.com/reference
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            venues = data.get('response').get('venues')
            return venues
        else:
            return []

class WeatherForecastCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide weather forecast
        update.message.reply_text("Here's the weather forecast for your destination:")
        pass

class AffordableEatsCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide affordable eating options
        update.message.reply_text("Here are some affordable places to eat in your destination:")
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

class HelpCommand(Command):
    def execute(self, update: Update, context: CallbackContext) -> None:
        # Your code to provide help or instructions
        update.message.reply_text("How can I assist you?")
        pass
    