from commands import Command
from telegram import Update
from telegram.ext import CallbackContext
from services import CacheService

tips_dictionary = {
    "PROMPT": "Kindly share your valuable travel insights and tips for exploring the enchanting city of {}",
    "ERROR": "Sorry, I couldn't suggest any tips for {} travel!",
    "WELCOME": "🌍 Ready for some travel tips about {}? Let's get started!",
    "CITY_NOT_FOUND": "Sorry, I couldn't find any travel tips for {}!",
    "FOLLOWING_QUESTION": ''
}


class Tips(Command):
    # OpenAIHelper and get_city_name are dependencies
    # injected into the Tips command in user_dialogue_helper
    def __init__(self, openai_helper, get_city_name, get_option_keyboard):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name
        self.get_tips_keyboard = get_option_keyboard

    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)

        travel_tips = self.get_tips(
            tips_dictionary['PROMPT'].format(city_name),
            context
        )

        if city_name:
            self.send_reply(
                update,
                tips_dictionary['WELCOME'].format(city_name),
            )

            self.handle_tips_found(
                update,
                context,
                city_name, travel_tips
            )
        else:
            self.send_reply(
                update,
                tips_dictionary['CITY_NOT_FOUND'].format(city_name)
            )

    def get_tips(self, prompt: str, context: CallbackContext) -> str:
        tips_cache_key = 'city_tips'

        cache_service = CacheService()
        cached_data = cache_service.get(tips_cache_key, context)

        if cached_data:
            return cached_data

        try:
            response = self.openai_helper.get_response(prompt)
            parse_response = self.parse_response(response)

            cache_service.set(
                tips_cache_key,
                parse_response,
                context
            )

            return parse_response
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""

    def parse_response(self, response: str) -> dict:
        if response and response['choices']:
            message = response['choices'][0]['message']['content']

            # Remove first sentence from the original text
            splitted_message = message.split('. ', 1)

            if len(splitted_message) > 1:
                # Return everything after the first period
                return splitted_message[1]
            else:
                # If there's no period, return the original text
                return message
        else:
            return {}

    def handle_tips_found(
        self,
        update: Update,
        context: CallbackContext,
        city_name: str,
        travel_tips: str
    ) -> None:
  
        self.send_reply(
            update,
            travel_tips,
            reply_markup=self.get_tips_keyboard()
        )

    def send_reply(
        self,
        update: Update,
        text: str,
        reply_markup = None
    ) -> None:
        update.message.reply_text(text, reply_markup=reply_markup)
