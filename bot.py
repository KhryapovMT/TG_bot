import logging
import datetime
import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_TOKEN = '6146264911:AAEUYFWgDYQNcjfYvk03kj0B2yTAJ__P890'

EMISSION_FACTORS = {
    "car": 0.23,
    "public_transport": 0.12,
    "bicycle": 0.02,
    "walking": 0.01
}

BADGES = {
    "bronze": {"threshold": 50, "name": "🥉 Bronze", "description": "Reduce 50 kg CO2e"},
    "silver": {"threshold": 100, "name": "🥈 Silver", "description": "Reduce 100 kg CO2e"},
    "gold": {"threshold": 200, "name": "🥇 Gold", "description": "Reduce 200 kg CO2e"},
}


class User:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.footprint = 0
        self.history = []
        self.achievements = []

    def store_transportation_data(self, mode, distance):
        emission = distance * EMISSION_FACTORS[mode]
        self.footprint += emission
        self.history.append({
            'mode': mode,
            'distance': distance,
            'emission': emission,
            'date': datetime.date.today().isoformat()
        })

    def update_achievements(self):
        footprint = self.footprint
        badge_message = ""

        for badge_id, badge_info in BADGES.items():
            if badge_id not in self.achievements and footprint >= badge_info['threshold']:
                self.achievements.append(badge_id)
                badge_message += f"🎉 Congratulations! You've just earned the {badge_info['name']} badge: {badge_info['description']}\n"

        return badge_message

class CarbonFootprintBot:
    def __init__(self, api_token):
        self.bot = telepot.Bot(api_token)
        self.users = {}
        self.waiting_for_distance = False
        self.current_user = None
        self.current_query_id = None
        self.current_query_data = None

    def start(self, chat_id):
        text = f"Hello! Welcome to the Carbon Footprint Calculator bot. 🌍\n"
        text += "To calculate your carbon footprint, please select your transportation mode below:\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Car 🚗', callback_data='car'),
             InlineKeyboardButton(text='Public Transport 🚌', callback_data='public_transport')],
            [InlineKeyboardButton(text='Bicycle 🚲', callback_data='bicycle'),
             InlineKeyboardButton(text='Walking 🚶‍♂️', callback_data='walking')]
        ])

        self.bot.sendMessage(chat_id, text, reply_markup=keyboard)

    def help(self, chat_id):
        help_text = "To use this bot, simply select your transportation mode and follow the instructions provided."
        help_text += " You can also use the following commands:\n"
        help_text += "/start - Start the bot and select transportation mode.\n"
        help_text += "/help - Show help information.\n"
        help_text += "/statistics - Show your carbon footprint statistics.\n"
        help_text += "/reset - Reset your carbon footprint data."
        self.bot.sendMessage(chat_id, help_text)

    def handle_help(self, chat_id):
        # Define the help message to send
        message = "To use this bot, simply select your transportation mode and follow the instructions provided."
        message += " You can also use the following commands:\n"
        message += "/start - Start the bot and select transportation mode.\n"
        message += "/help - Show help information.\n"
        message += "/statistics - Show your carbon footprint statistics.\n"
        message += "/reset - Reset your carbon footprint data."

        # Send the help message
        self.bot.sendMessage(chat_id, text=message)

    def handle_message(self, msg):
        # Handle incoming messages
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text' and self.waiting_for_distance and self.current_user.chat_id == chat_id:
            distance = float(msg['text'])
            self.current_user.store_transportation_data(self.current_query_data, distance)
            badge_message = self.current_user.update_achievements()
            self.bot.answerCallbackQuery(self.current_query_id, text="Distance saved. " + badge_message)
            self.waiting_for_distance = False

    def handle_callback_query(self, msg):
        # Handle inline button callbacks
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        user = self.users.get(chat_id)
        if user:
            self.bot.sendMessage(chat_id, text="Please enter the distance in km:")
            self.waiting_for_distance = True
            self.current_user = user
            self.current_query_id = query_id
            self.current_query_data = query_data


if __name__ == '__main__':
    # Start the bot and listen for updates
    bot = CarbonFootprintBot(API_TOKEN)
    MessageLoop(bot.bot, {
        'chat': bot.handle_message,
        'callback_query': bot.handle_callback_query
    }).run_as_thread()
    print("Listening for updates...")
 
