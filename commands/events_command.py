import requests
from commands import Command
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from messages import DEFAULT_USER_NAME

class Events(Command):
    def __init__(self,get_city_name, get_option_keyboard, logger):
        self.get_city_name = get_city_name
        self.get_events_keyboard = get_option_keyboard
        self.logger = logger

    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)

        events = self.get_events(city_name)
        
        if events:
            self.send_reply(
                update,
                f"Here are some interesting events in {city_name} for you, {user_name}! 🎉🎉🎉"
            )

            self.post_events(update, events)
        else:
            self.send_reply(update, f"No events found in {city_name} 😢")

    def get_events(self, city_name: str) -> dict:        
        try:
            response = requests.get(
                "https://app.ticketmaster.com/discovery/v2/events.json",
                params={
                    "size": 20,
                    "city": city_name,
                    "classificationName": "music",
                    "apikey": "OJyV7LkLamuqxx7H2gDJdCVPdCMxHSAe",
                })
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get('_embedded', {}).get('events', [])
            else:
                # Handle errors with a more informative message or raise an exception
                response_data = response.json()
                error_message = response_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(f"API Error: {error_message}")
        except Exception as e:
            self.logger.log('error', f"An error occurred while fetching events: {e}")

    def post_events(self, update: Update, events: list) -> None:
        for event in events:
            update.message.reply_text(
                self.parse_events_payload(event),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
    
    def parse_events_payload(self, event: dict) -> str:        
        event_name = event.get('name', '').replace('<', '&lt;').replace('>', '&gt;')
        event_date = event.get('dates', {}).get('start', {}).get('localDate')
        event_time = event.get('dates', {}).get('start', {}).get('localTime')
        event_venue = event.get('_embedded', {}).get('venues', [{}])[0].get('name')
        event_address = event.get('_embedded', {}).get('venues', [{}])[0].get('address', {}).get('line1')
        event_city = event.get('_embedded', {}).get('venues', [{}])[0].get('city', {}).get('name')
        event_url = event.get('url')
        
        # Image
        event_image = event.get('images', [{}])[0].get('url')
        
        # Genre and Classification
        genre = event.get('classifications', [{}])[0].get('genre', {}).get('name')
        
        # Construct the message
        message = (
            f"🎉 Event: {event_name}\n"
            f"📅 Date: {event_date}\n"
            f"⏰ Time: {event_time}\n"
            f"🏢 Venue: {event_venue}, {event_city}\n"
            f"📍 Address: {event_address}\n"
            f"🔗 [Buy Tickets]({event_url})\n"
            f"📸 [Event Image]({event_image})\n"
            f"📊 Genre: {genre}\n"
        )
        
        return message
    
    def send_reply(
        self,
        update: Update,
        text: str,
        reply_markup = None
    ) -> None:
        update.message.reply_text(text, reply_markup=reply_markup)
