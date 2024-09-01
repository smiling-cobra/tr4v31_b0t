from telegram import Update
from telegram.ext import CallbackContext
from commands import Command
from services import CacheService

stories_dictionary = {
    "PROMPT": "Share please some fascinating facts about {}",
    "ERROR": "Sorry, I couldn't find any facts about {}!",
    "WELCOME": "🤓 Sure thing! Let me share some fascinating facts about {} with you.",
}


class Stories(Command):
    # OpenAIHelper and get_city_name are dependencies
    # injected into the Stories command in user_dialogue_helper
    def __init__(self, openai_helper, get_city_name, get_option_keyboard):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name
        self.get_stories_keyboard = get_option_keyboard

    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)

        city_facts = self.get_city_stories(
            stories_dictionary['PROMPT'].format(city_name),
            context
        )

        if city_facts:
            self.handle_founded_stories(
                update,
                context,
                city_name,
                city_facts
            )
        else:
            self.send_reply(
                stories_dictionary['ERROR'].format(city_name)
            )

    def get_city_stories(self, prompt: str, context: CallbackContext) -> str:
        stories_cache_key = 'city_facts'

        cache_service = CacheService()
        cached_data = cache_service.get(stories_cache_key, context)
        
        if cached_data:
            return cached_data
        
        try:
            response = self.openai_helper.get_response(prompt)
            parsed_response = self.parse_response(response)

            cache_service.set(
                stories_cache_key,
                parsed_response,
                context
            )

            return parsed_response
        except Exception as e:
            print(f"An error while get_city_stories {e}")
            return ""

    def parse_response(self, response: str) -> dict:
        if response and response['choices']:
            return response['choices'][0]['message']['content']
        else:
            print("An error occurred while making response in Stories")
            return {}

    def handle_founded_stories(
        self,
        update: Update,
        context: CallbackContext,
        city_name: str,
        city_facts: str
    ) -> None:

        self.send_reply(
            update,
            stories_dictionary['WELCOME'].format(city_name),
        )

        self.send_reply(
            update,
            city_facts,
            reply_markup=self.get_stories_keyboard()
        )

    def send_reply(
        self,
        update: Update,
        text: str,
        reply_markup = None
    ) -> None:
        update.message.reply_text(text, reply_markup=reply_markup)
