import html
import requests
from datetime import date
from abc import ABC, abstractmethod
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from common import get_lobby_keyboard
from commands import Command


class Stories(Command):
    # OpenAIHelper is a dependency that we inject into the Stories command
    def __init__(self, openai_helper):
        self.openai_helper = openai_helper
        
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        
        if city_name:
            city_facts = self.get_facts(f"Tell me some interesting facts about {city_name}")
        else:
            city_facts = ""
        
        if city_facts:
            update.message.reply_text(f"Here are some facts about {city_name}:")
            update.message.reply_text(city_facts)
        else:
            update.message.reply_text(f"Sorry, I couldn't find any facts about {city_name}!")
        
    def get_facts(self, prompt: str) -> str:
        try:
            response = response = self.openai_helper.get_response(prompt)
            return self.get_response(response)
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""
    
    def get_response(self, response: str) -> dict:
        if response and response['choices']:
            message = response['choices'][0]['message']['content']
            return message
        else:
            return {}
    
    def get_city_name(self, context: CallbackContext) -> str:
        city_data = context.user_data.get('city_data')[0]
        address_components = city_data.get('address_components')[0]
        city_name = address_components.get('long_name')
        return city_name