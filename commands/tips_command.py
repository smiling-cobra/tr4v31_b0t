from commands import Command
from telegram import Update
from telegram.ext import CallbackContext

tips_dictionary = {
    "PROMPT": "Kindly share your valuable travel insights and tips for exploring the enchanting city of {}",
    "ERROR": "Sorry, I couldn't suggest any tips for {} travel!",
    "WELCOME": "🌍 Ready for some travel tips about {}? Let's get started!",
    "CITY_NOT_FOUND": "Sorry, I couldn't find any travel tips for {}!",
}


class Tips(Command):
    # OpenAIHelper and get_city_name are dependencies
    # injected into the Tips command in user_dialogue_helper
    def __init__(self, openai_helper, get_city_name):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name

    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)

        if city_name:
            travel_tips = self.get_tips(
                tips_dictionary['PROMPT'].format(city_name)
            )
        else:
            update.message.reply_text(
                tips_dictionary['CITY_NOT_FOUND'].format(city_name)
            )

        if travel_tips:
            update.message.reply_text(
                tips_dictionary['WELCOME'].format(city_name)
            )
            context.user_data['city_tips'] = travel_tips
            update.message.reply_text(travel_tips)
        else:
            update.message.reply_text(
                tips_dictionary['ERROR'].format(city_name)
            )

    def get_tips(self, prompt: str) -> str:
        try:
            response = self.openai_helper.get_response(prompt)
            return self.parse_response(response)
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""

    def parse_response(self, response: str) -> dict:
        if response and response['choices']:
            message = response['choices'][0]['message']['content']
            return message
        else:
            return {}
