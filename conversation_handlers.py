# conversation_handlers.py

from telegram.ext import ConversationHandler, MessageHandler, Filters
from main import get_destination, end_conversation, start_command

# States
DESTINATION, END = range(2)

# Create the conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        DESTINATION: [MessageHandler(Filters.text & ~Filters.command, get_destination)],
        END: [MessageHandler(Filters.text & ~Filters.command, end_conversation)],
    },
    fallbacks=[],
)
