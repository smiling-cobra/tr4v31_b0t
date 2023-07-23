import os
from typing import Final
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from messages import WELCOME_MESSAGE_LONG, WELCOME_MESSAGE_CONCISE

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')
bot_username = os.environ.get('BOT_USERNAME')

# Handlers
def start_command(update: Update, context: CallbackContext):
    update.message.reply_text(WELCOME_MESSAGE_CONCISE)
    return get_destination()

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text('I`m your travel assistant. Please, type something so I can respond!')

def custom_command(update: Update, context: CallbackContext):
    update.message.reply_text('This is a custom command!')

def get_destination(update: Update, context: CallbackContext) -> int:
    destination = update.message.text
    update.message.reply_text(f"Great choice! You're heading to {destination}. 🏖️\n\nNow I'll provide you with useful information about your destination.")
    print('DESTINATION:', destination)
    # # Add your logic to handle the destination here...
    # return END

# Messages
def handle_message(update: Update, context: CallbackContext):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User({update.message.chat.id}) in {message_type} : "{text}"')
    
    # This block is to handle cases when you want to mention [travel_bot] directly in group chat.
    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)
    
    print('Bot:', response)
    update.message.reply_text(response)

# Responses
def handle_response(message: str) -> str:
    message_to_lowercase: str = message.lower()

    print('message:', message)

    if 'hello' in message_to_lowercase:
        return 'Hey there!'
    
    if 'how are you' in message_to_lowercase:
        return 'I am good!'
    
    if 'i love python' in message_to_lowercase:
        return 'Don`t forget to subscribe!'
    
    return 'Please, clarify your question.'

# Log errors
def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')

# Main function
def main() -> None:
    print('Starting bot...')
    # app = Application.builder().token(telegram_bot_token).build()

    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher

    # Commands
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('custom', custom_command))

    # Messages
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Errors
    dispatcher.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()