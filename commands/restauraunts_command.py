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

    
class Restauraunts(Command):
    def __init__(self, photo_retriever, get_city_name):
        self.photo_retriever = photo_retriever
        self.get_city_name = get_city_name
    
    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)
        restaurants = self.get_restauraunts(city_name)
        
        # Save the restaurants in the user's context
        context.user_data['affordable_eats'] = restaurants
        
        update.message.reply_text(create_welcome_restaurants_message(user_name, city_name), reply_markup=self.get_affordable_eats_keyboard(context))
        self.post_restauraunts(update, context, restaurants)
    
    def format_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'
    
    def get_affordable_eats_keyboard(self, context: CallbackContext) -> InlineKeyboardMarkup:
        city_name = self.get_city_name(context)
        return ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")], [KeyboardButton(f"🥗 Show me more restaurants in {city_name}!")]])
        
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
            shuffled_venues = random.shuffle(venues)
            for venue in venues:
                venue_id = venue.get('fsq_id')
                venue['photo'] = self.photo_retriever.get_venue_photos(venue_id)
            return venues
        else:
            return []
    
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