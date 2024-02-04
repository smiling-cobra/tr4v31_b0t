import requests
from commands import Command
from telegram import Update
from telegram.ext import CallbackContext
import logging
from messages import DEFAULT_USER_NAME

events_dict = {
    'FOLLOWING_QUESTION': "🥗 Show me more events in {}!"
}


class Events(Command):
    def __init__(self,get_city_name, get_option_keyboard):
        self.get_city_name = get_city_name
        self.get_events_keyboard = get_option_keyboard

    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)

        try:
            update.message.reply_text(f"Here are some interesting events for you, {user_name}! 🎉🎉🎉")
            events = self.fetch_events(city_name)
            
            if events and len(events) > 0:
                self.post_events(update, events)
            else:
                update.message.reply_text("No events found for your city. 😢")
                update.message.reply_text(
                    "Would you like to do anything else?",
                    events_dict['FOLLOWING_QUESTION'].format(city_name)
                )
        except Exception as e:
            logging.error(error_message)
            update.message.reply_text("An error occurred while fetching events.")

    def fetch_events(self, city_name: str) -> dict:        
        params = {
            "size": 1,
            "city": city_name,
            "classificationName": "music",
            "apikey": "OJyV7LkLamuqxx7H2gDJdCVPdCMxHSAe",
        }

        response = requests.get("https://app.ticketmaster.com/discovery/v2/events.json", params=params)
        
        if response.status_code == 200:
            data = response.json()
            all_events = data.get('_embedded', {}).get('events', [])
            return all_events
        else:
            # Handle errors with a more informative message or raise an exception
            response_data = response.json()
            error_message = response_data.get('error', {}).get('message', 'Unknown error')
            raise Exception(f"API Error: {error_message}")
    
    def parse_events_payload(self, events: dict) -> str:
        event = events[0]
        event_name = event.get('name')
        event_date = event.get('dates', {}).get('start', {}).get('localDate')
        event_time = event.get('dates', {}).get('start', {}).get('localTime')
        event_venue = event.get('_embedded', {}).get('venues', [{}])[0].get('name')
        event_url = event.get('url')
        
        event_message = f"🎉 {event_name}\n📅 {event_date}\n⏰ {event_time}\n🏢 {event_venue}\n🔗 {event_url}"
        print('EVENT MESSAGE ===>', event_message)
        return event_message

    def post_events(self, update: Update, events: list) -> None:
        for event in events:
            event_message = self.parse_events_payload(event)
            update.message.reply_text(event_message)
