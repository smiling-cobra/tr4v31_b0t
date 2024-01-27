import os
import html
import random
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext
from commands import Command
from messages import create_welcome_restaurants_message

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
foursquare_auth_key = os.environ.get('FOURSQUARE_API_KEY')

# Refactor this class. Extract restaraunt fetching logic into a separate class RestaurauntRetriever
class Restauraunts(Command):
    def __init__(self, photo_retriever, get_city_name):
        self.photo_retriever = photo_retriever
        self.get_city_name = get_city_name
    
    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)
        restaurants = self.get_restauraunts(city_name)
        
        # Save the restaurants in the user's context
        context.user_data['city_restauraunts'] = restaurants
        
        update.message.reply_text(
            create_welcome_restaurants_message(user_name, city_name),
            reply_markup=self.get_affordable_eats_keyboard(context)
        )
        self.post_restauraunts(update, restaurants)
    
    def format_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'
    
    def get_affordable_eats_keyboard(self, context: CallbackContext) -> InlineKeyboardMarkup:
        city_name = self.get_city_name(context)
        return ReplyKeyboardMarkup(
            [[KeyboardButton("🔙 Back")],
             [KeyboardButton(f"🥗 Show me more restaurants in {city_name}!")]]
        )
        
    def get_restauraunts(self, city_name: str) -> list:
        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'near': city_name,
            'query': 'restaurants',
            'limit': 50,
            'fields' :'name,location,fsq_id,distance,link',
        }

        headers = {
            "accept": "application/json",
            "Authorization": foursquare_auth_key
        }

        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            venues = data.get('results')
            
            # Debugging: Check if venues is a list
            if not isinstance(venues, list):
                print(f"Expected 'venues' to be a list, got: {type(venues)}")
                return []

            # Debugging: Print the length of venues before shuffling
            print(f"Number of venues before shuffling: {len(venues)}")

            # Shuffle the venues
            random.shuffle(venues)

            # Take only the first 7 venues from the shuffled list
            selected_venues = venues[:7]

            # Debugging: Print the length of venues after shuffling
            print(f"Number of venues after shuffling: {len(venues)}")
            
            for venue in selected_venues:
                venue_id = venue.get('fsq_id')
                if venue_id:
                    venue['photo'] = self.photo_retriever.get_venue_photos(venue_id)
                else:
                    print("Venue ID not found for a venue")

            return selected_venues
        else:
            print("get_restauraunts failed")
            return []
    
    def post_restauraunts(self, update: Update, restaurants: list) -> None:
        for restaurant in restaurants:
            restaurant_name = restaurant.get('name')
            restaurant_location = restaurant.get('location').get('formatted_address')
            restaurant_photo = restaurant.get('photo')
            
            if restaurant_photo:
                update.message.reply_photo(photo=restaurant_photo)
            
            restaurant_location_as_link = self.format_address_as_link(restaurant_location)
            message_text = f"{restaurant_name}\n{restaurant_location_as_link}"
            update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)