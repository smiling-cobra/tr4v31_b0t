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

forecast_cache_key = 'city_forecast'

class Weather(Command):
    def __init__(self, get_city_name, get_option_keyboard, logger):
        self.get_city_name = get_city_name
        self.get_weather_keyboard = get_option_keyboard
        self.logger = logger

    def execute(self, update: Update, context: CallbackContext) -> None:
        self.post_weather_forecast(update, context)

    def post_weather_forecast(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            create_weather_message(
                update.message.chat.first_name or DEFAULT_USER_NAME,
                self.get_city_name(context),
                self.prepare_weather_summary(update, context)
            ),
            reply_markup=self.get_weather_keyboard()
        )
    
    def prepare_weather_summary(self, update: Update, context: CallbackContext):
        city_coordinates = self.get_city_coordinates(context)
        weather_forecast = self.get_weather_forecast(city_coordinates, context)
        return weather_forecast.get('daily')[0].get('summary')

    def get_city_coordinates(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        return {
            'lat': city_data.get('geometry').get('location').get('lat'),
            'lng': city_data.get('geometry').get('location').get('lng')
        }

    def get_weather_forecast(
        self,
        city_coordinates: dict,
        context: CallbackContext
    ) -> list:
        cache_service = CacheService()

        cached_forecast = cache_service.get(
            forecast_cache_key,
            context
        )

        if cached_forecast:
            return cached_forecast

        weather_url = weather_api_url.format(
            lat=city_coordinates.get("lat"),
            lon=city_coordinates.get("lng"),
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