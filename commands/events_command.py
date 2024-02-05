import requests
from commands import Command
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from messages import DEFAULT_USER_NAME

events_dict = {
    'FOLLOWING_QUESTION': "🥗 Show me more events in {}!"
}


class Events(Command):
    def __init__(self,get_city_name, get_option_keyboard, logger):
        self.get_city_name = get_city_name
        self.get_events_keyboard = get_option_keyboard
        self.logger = logger

    def execute(self, update: Update, context: CallbackContext) -> None:
        user_name = update.message.chat.first_name or DEFAULT_USER_NAME
        city_name = self.get_city_name(context)

        try:
            update.message.reply_text(f"Here are some interesting events for you, {user_name}! 🎉🎉🎉")
            events = self.fetch_events(city_name)
            
            if events:
                self.post_events(update, events)
                
                update.message.reply_text(
                    'Cool! Would you like to see more events? 🎉🎉🎉',
                    reply_markup=self.get_events_keyboard(
                        events_dict['FOLLOWING_QUESTION'].format(city_name)
                    )
                )
            else:
                update.message.reply_text("No events found for your city. 😢")
                update.message.reply_text(
                    "Would you like to do anything else?",
                    events_dict['FOLLOWING_QUESTION'].format(city_name)
                )
        except Exception as e:
            self.logger.log('error', f"An error occurred while fetching events: {e}")
            update.message.reply_text(f"An error occurred while fetching events: {e}")

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
    
    def parse_events_payload(self, event: dict) -> str:
        event_name = event.get('name')
        event_date = event.get('dates', {}).get('start', {}).get('localDate')
        event_time = event.get('dates', {}).get('start', {}).get('localTime')
        event_venue = event.get('_embedded', {}).get('venues', [{}])[0].get('name')
        event_url = event.get('url')
        
        return f"🎉 {event_name}\n📅 {event_date}\n⏰ {event_time}\n🏢 {event_venue}\n🔗 {event_url}"

    def post_events(self, update: Update, events: list) -> None:
        for event in events:
            update.message.reply_text(
                self.parse_events_payload(event),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True    
            )
