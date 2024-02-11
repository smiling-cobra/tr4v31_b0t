import os
import html
import requests
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from commands import Command
from messages import (
    create_welcome_restaurants_message,
    DEFAULT_USER_NAME
)
from services import CacheService

client_id = os.environ.get('FOURSQUARE_CLIENT_ID')
client_secret = os.environ.get('FOURSQUARE_CLIENT_SECRET')
base_url = os.environ.get('FOURSQSARE_API_URL')
foursquare_auth_key = os.environ.get('FOURSQUARE_API_KEY')

rest_dict = {
    'FOLLOWING_QUESTION': "🥗 Show me more restaurants in {}!"
}


# Refactor this class.
# Extract restaraunt fetching logic
# into a separate class RestaurauntRetriever
class Restauraunts(Command):
    def __init__(self, photo_retriever, get_city_name, get_option_keyboard):
        self.photo_retriever = photo_retriever
        self.get_city_name = get_city_name
        self.get_rest_keyboard = get_option_keyboard

    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)
        restaurants = self.get_restauraunts(city_name, context)

        # Save the restaurants in the user's context
        context.user_data['city_restauraunts'] = restaurants

        update.message.reply_text(
            create_welcome_restaurants_message(user_name, city_name),
            reply_markup=self.get_rest_keyboard(
                rest_dict['FOLLOWING_QUESTION'].format(city_name)
            )
        )
        self.post_restauraunts(update, restaurants)

    def get_address_as_link(self, address: str):
        google_maps_link = f'https://www.google.com/maps/search/?api=1&query={html.escape(address)}'
        return f'<a href="{google_maps_link}">{html.escape(address)}</a>'

    def get_restauraunts(self, city_name: str, context: CallbackContext) -> list:
        restauraunts_cache_key = 'city_restauraunts'
        cache_service = CacheService()
        cached_restauraunts = cache_service.get(
            restauraunts_cache_key,
            context
        )

        if cached_restauraunts:
            return cached_restauraunts

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'near': city_name,
            'query': 'restaurants',
            'limit': 50,
            'fields': 'name,location,fsq_id,distance,link',
        }

        headers = {
            "accept": "application/json",
            "Authorization": foursquare_auth_key
        }

        response = requests.get(
            base_url,
            params=params,
            headers=headers
        )

        try:
            data = response.json()
        except ValueError as e:
            return []
            print(f"Error parsing JSON: {e}")

        if response.status_code == 200:
            venues = data.get('results', [])

            for venue in venues:
                venue_id = venue.get('fsq_id')
                if venue_id:
                    venue['photo'] = self.photo_retriever.get_venue_photos(
                        venue_id
                    )
                else:
                    print("Venue ID not found for a venue")

            cache_service.set(
                restauraunts_cache_key,
                venues,
                context
            )

            return venues[:7]
        else:
            print("get_restauraunts failed")
            return []

    def post_restauraunts(self, update: Update, restaurants: list) -> None:
        for restaurant in restaurants:
            restaurant_name = restaurant.get('name')
            restaurant_location = (
                restaurant.get('location')
                .get('formatted_address')
            )
            restaurant_photo = restaurant.get('photo')

            if restaurant_photo:
                update.message.reply_photo(photo=restaurant_photo)

            location_link = self.get_address_as_link(restaurant_location)
            message_text = f"{restaurant_name}\n{location_link}"
            update.message.reply_text(
                message_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
