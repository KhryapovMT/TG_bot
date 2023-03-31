import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import UpdateQueue, CommandHandler, CallbackQueryHandler, MessageHandler
import requests
import json
import datetime

# Set up the logging
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

queue = UpdateQueue()
updater = Updater(API_TOKEN, update_queue=queue)

dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
def start(update: Update, context):
    user = update.effective_user
    context.user_data.setdefault('footprint', 0)
    context.user_data.setdefault('history', [])
    
    text = f"Hello {user.first_name}! Welcome to the Carbon Footprint Calculator bot. 🌍\n"
    text += "To calculate your carbon footprint, please select your transportation mode below:\n"
    
    keyboard = [
        [InlineKeyboardButton("Car 🚗", callback_data="car"),
         InlineKeyboardButton("Public Transport 🚌", callback_data="public_transport"),
         InlineKeyboardButton("Bicycle 🚲", callback_data="bicycle"),
         InlineKeyboardButton("Walking 🚶‍♂️", callback_data="walking")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)


def help_command(update: Update, context):
    help_text = "To use this bot, simply select your transportation mode and follow the instructions provided."
    help_text += " You can also use the following commands:\n"
    help_text += "/start - Start the bot and select transportation mode.\n"
    help_text += "/help - Show help information.\n"
    help_text += "/statistics - Show your carbon footprint statistics.\n"
    help_text += "/reset - Reset your carbon footprint data."
    update.message.reply_text(help_text)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))

def format_statistics(user_data, time_period=None):
    if time_period is not None:
        start_date = datetime.date.today() - datetime.timedelta(days=time_period)
        history = [entry for entry in user_data['history'] if datetime.date.fromisoformat(entry['date']) >= start_date]
    else:
        history = user_data['history']

    total_emission = sum(entry['emission'] for entry in history)
    mode_emissions = {mode: 0 for mode in EMISSION_FACTORS.keys()}
    for entry in history:
        mode_emissions[entry['mode']] += entry['emission']
    
    text = "Carbon Footprint Statistics:\n"
    text += f"{'Mode':<17}{'Emission (kg CO2e)'}\n"
    for mode, emission in mode_emissions.items():
        text += f"{mode.capitalize():<17}{emission:.2f}\n"
    text += f"{'Total':<17}{total_emission:.2f}"
    return text

def statistics(update: Update, context):
    time_period = None
    if 'period' in context.user_data:
        time_period = context.user_data['period']
    
    text = format_statistics(context.user_data, time_period)
    update.message.reply_text(text)

dispatcher.add_handler(CommandHandler("statistics", statistics))

def store_transportation_data(user_data, mode, distance):
    emission = distance * EMISSION_FACTORS[mode]
    user_data['footprint'] += emission
    user_data['history'].append({
        'mode': mode,
        'distance': distance,
        'emission': emission,
        'date': datetime.date.today().isoformat()
    })

def update_achievements(user_data):
    footprint = user_data['footprint']
    achievements = user_data.get('achievements', [])

    badge_message = ""

    for badge_id, badge_info in BADGES.items():
        if badge_id not in achievements and footprint >= badge_info['threshold']:
            achievements.append(badge_id)
            badge_message += f"🎉 Congratulations! You've just earned the {badge_info['name']} badge: {badge_info['description']}\n"

    if badge_message:
        user_data['achievements'] = achievements

    return badge_message

def achievements(update: Update, context):
    achievements = context.user_data.get("achievements", [])
    if not achievements:
        update.message.reply_text("You haven't earned any badges yet. Keep reducing your carbon footprint to unlock achievements!")
        return

    text = "🏆 Your Achievements:\n\n"
    for badge_id in achievements:
        badge = BADGES[badge_id]
        text += f"{badge['name']} - {badge['description']}\n"
    
    update.message.reply_text(text)

dispatcher.add_handler(CommandHandler("achievements", achievements))

def share(update: Update, context):
    user = update.effective_user
    achievements = context.user_data.get("achievements", [])
    if not achievements:
        update.message.reply_text("You don't have any achievements to share yet.")
        return

    text = f"{user.first_name} has been using the Carbon Footprint Calculator bot and has earned the following achievements:\n\n"
    for badge_id in achievements:
        badge = BADGES[badge_id]
        text += f"{badge['name']} - {badge['description']}\n"
    
    text += "\nJoin the carbon footprint reduction journey using the Carbon Footprint Calculator bot: https://t.me/Habitr_bot"
    update.message.reply_text(text)  # This line was missing

dispatcher.add_handler(CommandHandler("share", share))
    
def reset(update: Update, context):
    context.user_data['footprint'] = 0
    context.user_data['history'] = []
    update.message.reply_text("Your carbon footprint data has been reset.")

dispatcher.add_handler(CommandHandler("reset", reset))
def main():
    # Start the bot
    updater.start_polling()
    print("Carbon Footprint Calculator bot is running...")

    # Run the bot until the user presses Ctrl+C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()
    print("Carbon Footprint Calculator bot has been stopped.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        updater.stop()
        print("\nCarbon Footprint Calculator bot has been stopped.")
