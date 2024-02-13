import os
import requests
from telegram import Update
from telegram.ext import CallbackContext
from commands import Command
from messages import (
    TELL_ME_MORE_ABOUT_WEATHER_MESSAGE,
    create_weather_message,
    DEFAULT_USER_NAME
)
from services import CacheService

weather_api_key = os.environ.get('OPEN_WEATHER_API_KEY')
weather_api_url = os.environ.get('OPEN_WEATHER_API_URL')


class Weather(Command):
    def __init__(self, get_city_name, get_option_keyboard):
        self.get_city_name = get_city_name
        self.get_weather_keyboard = get_option_keyboard

    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)
        city_coordinates = self.get_city_coordinates(context)

        weather_now = self.get_forecast(city_coordinates, context)
        weather_desc = weather_now.get('daily')[0].get('summary')

        update.message.reply_text(
            create_weather_message(user_name, city_name, weather_desc),
            reply_markup=self.get_weather_keyboard(
                TELL_ME_MORE_ABOUT_WEATHER_MESSAGE
            )
        )

    def get_city_coordinates(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        lat = city_data.get('geometry').get('location').get('lat')
        lng = city_data.get('geometry').get('location').get('lng')
        return {'lat': lat, 'lng': lng}

    def get_forecast(
        self,
        city_coordinates: dict,
        context: CallbackContext
    ) -> list:
        forecast_cache_key = 'city_forecast'
        cache_service = CacheService()
        cached_forecast = cache_service.get(forecast_cache_key, context)
        
        if cached_forecast:
            return cached_forecast
        
        lat = city_coordinates.get("lat")
        lon = city_coordinates.get("lng")
        
        weather_url = weather_api_url.format(
            lat=lat,
            lon=lon,
            weather_api_key=weather_api_key
        )

        response = requests.get(weather_url)

        if response.status_code == 200:
            weather_data = response.json()
            
            cache_service.set(
                forecast_cache_key,
                weather_data,
                context
            )
            
            return weather_data
        else:
            return []
