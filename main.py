from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')
bot_username = os.environ.get('BOT_USERNAME')

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Welcome to travel bot!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('I`m your travel assistant. Please, type something so I can respond!')

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('This is a custom command!')    

# Responses
def handle_response(message: str) -> str:
    message_to_lowercase: str = message.lower()

    if 'hello' in message_to_lowercase:
        return 'Hey there!'
    
    if 'how are you' in message_to_lowercase:
        return 'I am good!'
    
    if 'i love python' in message_to_lowercase:
        return 'Don`t forget to subscribe!'
    
    return 'Please, clarify your question.'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(response)

# Log errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

# Run the program
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(telegram_bot_token).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    app.run_polling(poll_interval=3)