import os
import random
import logging
from collections import defaultdict
import requests
import json
import datetime
import sqlite3

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters


# Set up the logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_TOKEN = '6157683300:AAGYWHBTEATMtxzcqASDPTT-rmAvLTtOP3A'

EMISSION_FACTORS = {
    "car": 0.23,
    "public_transport": 0.12,
    "bicycle": 0.02,
    "walking": 0.01
}

POINTS = {
    "car": 1,
    "public_transport": 2,
    "bicycle": 5,
    "walking": 10
}

BADGES = {
    "bronze": {"threshold": 50, "name": "🥉 Bronze", "description": "Reduce 50 kg CO2e"},
    "silver": {"threshold": 100, "name": "🥈 Silver", "description": "Reduce 100 kg CO2e"},
    "gold": {"threshold": 200, "name": "🥇 Gold", "description": "Reduce 200 kg CO2e"},
}

updater = Updater(API_TOKEN, use_context=True)

dispatcher = updater.dispatcher

commands_text = """Here are the available commands:
/start - Start the bot
/help - Show help message
/calculate - Calculate carbon footprint for a mode of transportation
/statistics - Show your carbon footprint statistics
/leaderboard - Show the leaderboard
/reset - Reset your data
"""

def start(update, context):
    start_text = f"Welcome to the Carbon Footprint Calculator bot! 🌎\nThis bot will help you calculate your carbon footprint based on your mode of transportation and distance traveled. You can use the following commands:\n{commands_text}"
    update.message.reply_text(start_text)

def help(update, context):
    help_text = f"Here are the available commands:\n{commands_text}"
    update.message.reply_text(help_text)

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

def calculate(update, context):
    text = "Please select a mode of transportation:"
    keyboard = [
        [
            InlineKeyboardButton("Car 🚗", callback_data="car"),
            InlineKeyboardButton("Public Transport 🚌", callback_data="public_transport"),
            InlineKeyboardButton("Bicycle 🚲", callback_data="bicycle"),
            InlineKeyboardButton("Walking 🚶‍♂️", callback_data="walking"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)

calculate_handler = CommandHandler('calculate', calculate)
dispatcher.add_handler(calculate_handler)

def transportation_mode_callback(update, context):
    query = update.callback_query
    query.answer()

    mode = query.data
    context.user_data['mode'] = mode

    text = f"You have chosen {mode.capitalize()}. Please enter the distance you traveled in kilometers (e.g. 10)."
    query.edit_message_text(text)

    return "GET_DISTANCE"

def statistics(update, context):
    text = "Your carbon footprint statistics will be displayed here."
    update.message.reply_text(text)
    
def get_distance_message(update, context):
    try:
        distance = float(update.message.text)
    except ValueError:
        update.message.reply_text("Invalid input. Please provide a numeric value for the distance.")
        return "GET_DISTANCE"

    mode = context.user_data['mode']
    emission_factor = EMISSION_FACTORS[mode]
    emission = emission_factor * distance

    context.user_data['footprint'] = context.user_data.get('footprint', 0) + emission

    today = datetime.date.today().isoformat()
    history_entry = {'date': today, 'mode': mode, 'distance': distance, 'emission': emission}
    context.user_data['history'].append(history_entry)

    store_transportation_data(update, context)

    text = f"You have traveled {distance} km using {mode.capitalize()}, emitting {emission:.2f} kg CO2e.\n\n"
    text += format_statistics(context.user_data)
    text += "\n\nWould you like to calculate another mode of transportation or view your statistics?"
    keyboard = [        [InlineKeyboardButton("Calculate Another", callback_data="another"),         InlineKeyboardButton("View Statistics", callback_data="statistics")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)

    return "CHOOSE_ACTION"

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    mode = query.data

    if mode not in EMISSION_FACTORS:
        query.answer("Invalid mode selected.")
        return

    query.answer()  # To acknowledge the button press

    distance = random.uniform(1, 10)  # Replace this with your actual distance input method
    emission = distance * EMISSION_FACTORS[mode]

    context.user_data['footprint'] += emission
    context.user_data['history'].append({
        "mode": mode,
        "distance": distance,
        "emission": emission,
        "date": datetime.date.today().isoformat()
    })

    store_transportation_data(update, context)

    text = f"You have chosen {mode.capitalize()} for {distance:.2f} km. This results in {emission:.2f} kg CO2e emission."
    query.edit_message_text(text)

def another_callback(update, context):
    query = update.callback_query
    query.answer()

    text = "Please select another mode of transportation:"
    keyboard = [
        [InlineKeyboardButton("Car 🚗", callback_data="car"),
         InlineKeyboardButton("Public Transport 🚌", callback_data="public_transport"),
         InlineKeyboardButton("Bicycle 🚲", callback_data="bicycle"),
         InlineKeyboardButton("Walking 🚶‍♂️", callback_data="walking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text, reply_markup=reply_markup)

    return "CHOOSE_TRANSPORTATION_MODE"

dispatcher.add_handler(CallbackQueryHandler(transportation_mode_callback, pattern="^(car|public_transport|bicycle|walking)$"))
dispatcher.add_handler(CallbackQueryHandler(statistics, pattern="^statistics$"))  
dispatcher.add_handler(CallbackQueryHandler(another_callback, pattern="^another$"))
dispatcher.add_handler(CallbackQueryHandler(button_callback))

def update_achievements(user_data):
    achievements = user_data.get("achievements", [])

    total_emission = user_data.get('footprint', 0)
    new_achievements = []
    for badge_id, badge in BADGES.items():
        if badge_id in achievements:
            continue
        if total_emission >= badge['threshold']:
            new_achievements.append(badge_id)
    
    if new_achievements:
        user_data['achievements'] = achievements + new_achievements
        text = "🎉 Congratulations on earning new achievements!\n\n"
        for badge_id in new_achievements:
            badge = BADGES[badge_id]
            text += f"{badge['name']} - {badge['description']}\n"
        return text

    return None

def store_transportation_data(update, context):
    mode = context.user_data.get('mode')
    if mode is None:
        update.message.reply_text("Error: Mode not found in user data.")
        return

    emission_factor = EMISSION_FACTORS.get(mode)
    if emission_factor is None:
        update.message.reply_text("Error: Emission factor not found for mode.")
        return

    history_entry = context.user_data['history'][-1]
    distance = history_entry['distance']
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    points = context.user_data['points']
    footprint = context.user_data['footprint']
    save_user_data(user_id, username, points, footprint)
    
    emission = emission_factor * distance
    context.user_data['footprint'] = context.user_data.get('footprint', 0) + emission
    context.user_data['history'].append({
        "date": datetime.date.today().isoformat(),
        "mode": mode,
        "distance": distance,
        "emission": emission
    })

    badge_message = update_achievements(context.user_data)

    if badge_message:
        update.message.reply_text(badge_message)

    points_earned = update_points(context.user_data, mode)
    update.message.reply_text(f"You have earned {points_earned} points for choosing {mode.capitalize()}!")

def update_points(user_data, mode):
    points = POINTS.get(mode, 0)
    user_data['points'] = user_data.get('points', 0) + points
    return points
  
def get_leaderboard_data():
    conn = sqlite3.connect('carbon_footprint.db')
    c = conn.cursor()

    c.execute('''SELECT username, points, footprint FROM users ORDER BY points DESC, footprint ASC''')
    leaderboard_data = c.fetchall()

    conn.close()
    return leaderboard_data

def format_leaderboard(leaderboard_data):
    text = "🏆 Leaderboard 🏆\n\n"
    for rank, (username, points, footprint) in enumerate(leaderboard_data, start=1):
        text += f"{rank}. {username} - {points} points, {footprint:.2f} kg CO2e\n"
    return text
 
def leaderboard(update, context):
    leaderboard_data = get_leaderboard_data()
    text = format_leaderboard(leaderboard_data)
    update.message.reply_text(text)

leaderboard_handler = CommandHandler('leaderboard', leaderboard)
dispatcher.add_handler(leaderboard_handler)

def reset(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data.clear()
    update.message.reply_text("All your data has been reset.")
    return "CHOOSE_ACTION"

reset_handler = CommandHandler('reset', reset)
dispatcher.add_handler(reset_handler)

def save_user_data(user_id, username, points, footprint):
    conn = sqlite3.connect('carbon_footprint.db')
    c = conn.cursor()

    c.execute("INSERT OR REPLACE INTO users (user_id, username, points, footprint) VALUES (?, ?, ?, ?)", (user_id, username, points, footprint))

    conn.commit()
    conn.close()

    if not c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            footprint REAL DEFAULT 0.0
        )''')

def update_points(user_data, mode):
    points = POINTS.get(mode, 0)
    user_data['points'] = user_data.get('points', 0) + points
    return points


def main():
    # Start the bot
    updater.start_polling()
    logger.info("Carbon Footprint Calculator bot is running...")

    # Run the bot until the user presses Ctrl+C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()
    logger.info("Carbon Footprint Calculator bot has been stopped.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        updater.stop()
        logger.info("\nCarbon Footprint Calculator bot has been stopped by user.")
