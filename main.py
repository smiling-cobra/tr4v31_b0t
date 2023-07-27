import os
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from messages import WELCOME_MESSAGE_LONG, WELCOME_MESSAGE_CONCISE

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')
bot_username = os.environ.get('BOT_USERNAME')
google_map_api_key = os.environ.get('GOOGLE_MAP_API_KEY')

# Define states for the conversation
DESTINATION, LOBBY = range(2)

# Handlers
def start(update: Update, context: CallbackContext):
    user_name = update.message.chat.first_name
    welcome_message = WELCOME_MESSAGE_CONCISE.format(user_name)
    update.message.reply_text(welcome_message)
    return DESTINATION

# def help_command(update: Update, context: CallbackContext):
#     update.message.reply_text('I`m your travel assistant. Please, type something so I can respond!')

# def custom_command(update: Update, context: CallbackContext):
#     update.message.reply_text('This is a custom command!')

# Function to handle the user's destination input
def get_destination(update: Update, context: CallbackContext):
    user_input = update.message.text
    # Add destination validation via Google Maps Geocoding API
    update.message.reply_text(f"Great! You're traveling to {user_input}. How can I assist you further?",
    reply_markup=get_lobby_keyboard())
    return LOBBY

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

# Function to create the bot lobby keyboard
def get_lobby_keyboard():
    # Define the options in the lobby
    options = [
        ['5 Facts', 'Tourist Attractions', 'Weather Forecast'],
        ['Affordable Eats', 'Local Phrases'],
        ['Travel Tips', 'Help', 'Exit']
    ]
    # Create a list of KeyboardButton objects for each row of options
    keyboard = [[KeyboardButton(option) for option in row] for row in options]
    # Return the ReplyKeyboardMarkup with the lobby keyboard
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

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

# Function to handle user's choice in the lobby
def handle_lobby_choice(update, context):
    user_choice = update.message.text
    # Handle the user's choice based on the selected option
    if user_choice == 'Tourist Attractions':
        # Your code to provide tourist attractions
        update.message.reply_text("Here are some popular tourist attractions in your destination:")
    elif user_choice == 'Weather Forecast':
        # Your code to provide weather forecast
        update.message.reply_text("Here's the weather forecast for your destination:")
    elif user_choice == 'Affordable Eats':
        # Your code to provide affordable eating options
        update.message.reply_text("Here are some affordable places to eat in your destination:")
    elif user_choice == 'Local Phrases':
        # Your code to provide local phrases
        update.message.reply_text("Here are some useful local phrases:")
    elif user_choice == 'Travel Tips':
        # Your code to provide travel tips
        update.message.reply_text("Here are some travel tips for your destination:")
    elif user_choice == 'Help':
        # Your code to provide help or instructions
        update.message.reply_text("How can I assist you?")

# Function to handle the '/cancel' command and end the conversation
def cancel(update: Update, context: CallbackContext):
    user_name = update.message.chat.first_name
    update.message.reply_text(f"Have a nice trip, {user_name}! Feel free to reach out again anytime!")
    reply_markup=ReplyKeyboardRemove()
    return ConversationHandler.END

# Log errors
def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')

# Main function
def main() -> None:
    print('Starting bot...')

    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher

    # Create the ConversationHandler to handle the onboarding process and lobby choices
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            DESTINATION: [MessageHandler(Filters.text & ~Filters.command, get_destination)],
            LOBBY: [MessageHandler(Filters.text & ~Filters.command, handle_lobby_choice)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add the ConversationHandler to the dispatcher
    dispatcher.add_handler(conv_handler)

    # Errors
    dispatcher.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()