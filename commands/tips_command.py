from commands import Command
from telegram import Update
from telegram.ext import CallbackContext

class Tips(Command):
    # OpenAIHelper and get_city_name are dependencies
    # injected into the Tips command in user_dialogue_helper
    def __init__(self, openai_helper, get_city_name):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name
        
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        prompt = f"Provide me with some useful travel tips for {city_name}"
        
        if city_name:
            travel_tips = self.get_tips(prompt)
        else:
            update.message.reply_text(f"Entshuldigung, there's something wrong with the city name {city_name}!")
        
        if travel_tips:
            update.message.reply_text(f"Here are some travel tips for {city_name}:")
            context.user_data['city_tips'] = travel_tips
            update.message.reply_text(travel_tips)
        else:
            update.message.reply_text(f"Sorry, I couldn't suggest any tips for {city_name} travel!")
    
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