from telegram import Update
from telegram.ext import CallbackContext
from commands import Command

stories_dictionary = {
    "PROMPT": "Share please some fascinating facts about {}",
    "ERROR": "Sorry, I couldn't find any facts about {}!",
    "WELCOME": "🤓 Sure thing! Let me share some fascinating facts about {} with you."
}


class Stories(Command):
    # OpenAIHelper and get_city_name are dependencies
    # injected into the Stories command in user_dialogue_helper
    def __init__(self, openai_helper, get_city_name):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name

    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)

        if city_name:
            city_facts = self.get_facts(
                stories_dictionary['PROMPT'].format(city_name)
            )
        else:
            print("An error occurred: No city name found!")
            city_facts = ""

        if city_facts:
            context.user_data['city_facts'] = city_facts
            update.message.reply_text(
                stories_dictionary['WELCOME'].format(city_name)
            )
            update.message.reply_text(city_facts)
        else:
            update.message.reply_text(
                stories_dictionary['ERROR'].format(city_name)
            )

    def get_facts(self, prompt: str) -> str:
        try:
            response = self.openai_helper.get_response(prompt)
            return self.get_response(response)
        except Exception as e:
            # Improved error logging
            print(f"An error while get_facts {e}")
            return ""

    def get_response(self, response: str) -> dict:
        if response and response['choices']:
            return response['choices'][0]['message']['content']
        else:
            print("An error occurred while making response in Stories")
            return {}
