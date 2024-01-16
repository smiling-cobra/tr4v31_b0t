from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

class GroupMessageHandler:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def group_message_handler(self, update: Update, context: CallbackContext):
        # Extract the message and chat details
        message = update.message
        chat = message.chat
        text = message.text

        print('Handling group message...!!!!!')
        
        # Check if the bot is mentioned in the group chat
        if f"@{context.bot.username}" in text:
            # Process the message following the mention
            response_text = process_group_message(text, chat.id)
            # Send a reply to the group
            message.reply_text(response_text)
        else:
            # Handle other group messages (if needed)
            # For instance, you can log the message or perform some actions
            # Note: Be mindful of privacy and group rules
            pass

    def setup(self):
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.group_message_handler))