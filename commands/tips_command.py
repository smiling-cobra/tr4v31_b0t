from commands import Command
from telegram import Update
from telegram.ext import CallbackContext

class Tips(Command):
    # OpenAIHelper is a dependency that we inject into the Tips command
    def __init__(self, openai_helper, get_city_name):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name
        
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        
        if city_name:
            travel_tips = self.get_tips(f"Provide me with some useful travel tips for {city_name}")
        else:
            update.message.reply_text(f"Entshuldigung, there's something wrong with the city name {city_name}!")
        
        if travel_tips:
            update.message.reply_text(f"Here are some travel tips for {city_name}:")
            update.message.reply_text(travel_tips)
        else:
            update.message.reply_text(f"Sorry, I couldn't suggest any tips for {city_name} travel!")
    
    def get_tips(self, prompt: str) -> str:
        try:
            response = response = self.openai_helper.get_response(prompt)
            return self.get_response(response)
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""