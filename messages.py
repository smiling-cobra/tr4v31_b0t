# messages.py

# User onboarding messages
WELCOME_MESSAGE_LONG = '''
🌍 Welcome to TravelBot! 🚀

🛩️ Are you excited about your upcoming journey? Let TravelBot be your trusty guide, providing you with all the essential information for your destination.

📍 To get started, please tell me where you're headed. Simply type the name of your destination city, and I'll fetch the best travel tips and valuable insights just for you!

🏖️ Whether it's exploring famous landmarks, trying local delicacies, or getting the latest weather forecast, TravelBot has got you covered.

🗺️ Traveling is an adventure, and TravelBot is here to make it even better. Type in your destination now to begin your journey!

🙌 Happy travels! If you need any help, just type /help to see what I can assist you with.
'''

WELCOME_MESSAGE_CONCISE = '''
🌍 Welcome to TravelBot, {}! 🚀

🛩️ Tell me your destination city, and I'll be your travel companion, providing valuable tips and insights for your trip!

🏖️ From famous landmarks to local cuisine and weather forecasts, TravelBot has got you covered.

🗺️ Let's get started! Type your destination city now and embark on a seamless travel experience.

🙌 Happy travels! For assistance, just type /help anytime.
'''

DEFAULT_USER_NAME = 'traveler'

HELP_WELCOME_MESSAGE = '''
Here's how you can use this bot: ...
'''

NO_CITY_FOUND_MESSAGE = '''
🤷‍♂️ Excusez-moi but no city was found... Try again!
'''

SHOW_MORE_LANDMARKS_MESSAGE = '''
"🗽 Show me more landmarks, please!"
'''

def create_initial_greeting_message(user_name, user_input) -> str:
    return f"🔥 Awesome, {user_name}! You're traveling to {user_input}! Here's what I can do ->"

def create_wrong_input_message(user_name) -> str:
    return f"🤷‍♂️ You've probably made a wrong input, {user_name}. Give it another try!"

def create_farewell_message(user_name) -> str:
    return f"👋 Have a nice trip, {user_name}! Feel free to reach out again anytime!"

def create_following_question_message(user_name) -> str:
    return f"Hey, {user_name}, what else can I help you with? 👀"

def create_welcome_landmarks_message(user_name, city_name) -> str:
    return f"📍 Here are some popular tourist attractions in {city_name}, {user_name} ->"

def create_welcome_restaurants_message(user_name, city_name) -> str:
    return f"🥗 Here are some affordable places to eat in {city_name}, {user_name} ->"