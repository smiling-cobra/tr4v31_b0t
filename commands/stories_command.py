import html
import requests
from datetime import date
from abc import ABC, abstractmethod
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from common import get_lobby_keyboard
from commands import Command


class Stories(Command):
    # OpenAIHelper and get_city_name are dependencies
    # injected into the Stories command in user_dialogue_helper
    def __init__(self, openai_helper, get_city_name):
        self.openai_helper = openai_helper
        self.get_city_name = get_city_name
        
    def execute(self, update: Update, context: CallbackContext) -> None:
        city_name = self.get_city_name(context)
        
        if city_name:
            city_facts = self.get_facts(f"Tell me some interesting facts about {city_name}")
        else:
            city_facts = ""
        
        if city_facts:
            context.user_data['city_facts'] = city_facts
            update.message.reply_text(f"Here are some facts about {city_name}:")
            update.message.reply_text(city_facts)
        else:
            update.message.reply_text(f"Sorry, I couldn't find any facts about {city_name}!")
        
    def get_facts(self, prompt: str) -> str:
        try:
            response = self.openai_helper.get_response(prompt)
            return self.get_response(response)
        except Exception as e:
            # Improved error logging
            print(f"An error occurred: {e}")
            return ""
    
    def get_response(self, response: str) -> dict:
        if response and response['choices']:
            return response['choices'][0]['message']['content']
        else:
            print(f"An error occurred while making response in Stories: {e}")
            return {}