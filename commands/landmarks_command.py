import os
import html
import requests
from datetime import date
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext
from commands import Command
from messages import create_welcome_landmarks_message, SHOW_MORE_LANDMARKS_MESSAGE

google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')

class Landmarks(Command):
    def __init__(self, get_city_name, get_option_keyboard):
        self.get_city_name = get_city_name
        self.get_landmark_keyboard = get_option_keyboard
        
    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)
        
        places = self.get_places(city_name)
        context.user_data['city_landmarks'] = places
        
        if places:
            update.message.reply_text(
                create_welcome_landmarks_message(user_name, city_name),
                reply_markup=self.get_landmark_keyboard(SHOW_MORE_LANDMARKS_MESSAGE)
            )
            self.post_landmarks(update, places)
        else:
            update.message.reply_text(f"Sorry, I couldn't find any landmarks in {city_name}!")
    
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
        
    def post_landmarks(self, update: Update, landmarks: list) -> None:
        for landmark in landmarks:
            landmark_name = landmark.get('name')                
            landmark_location = landmark.get('formatted_address')
            landmark_photo = landmark.get('photo')
            
            if landmark_photo:
                update.message.reply_photo(photo=landmark_photo)
                
            landmark_location_as_link = self.format_address_as_link(landmark_location)
            message_text = f"{landmark_name}\n{landmark_location_as_link}"
            update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)