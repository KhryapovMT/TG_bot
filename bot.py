import os
import random
import logging
from collections import defaultdict
import requests
import json
import datetime

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

def start(update, context):
    print("Start command received")  # Debugging line
    update.message.reply_text('Hello! I am your bot. Send me a message or use my commands!')

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

print("Bot is starting...")  # Debugging line
updater.start_polling()
print("Bot started.")  # Debugging line
updater.idle()

def transportation_mode_callback(update, context):
    query = update.callback_query
    query.answer()

    mode = query.data
    context.user_data['mode'] = mode

    text = f"You have chosen {mode.capitalize()}. Please enter the distance you traveled in kilometers (e.g. 10)."
    query.edit_message_text(text)

    return "GET_DISTANCE"

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
 
def main():
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

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

