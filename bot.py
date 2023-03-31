import logging
import datetime
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

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


class Form(StatesGroup):
    mode = State()
    distance = State()


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


async def start(message: types.Message):
    user = message.from_user
    async with FSMContext(message.chat.id) as state:
        await state.finish()

    text = f"Hello {user.first_name}! Welcome to the Carbon Footprint Calculator bot. 🌍\n"
    text += "To calculate your carbon footprint, please select your transportation mode below:\n"

    keyboard = [
        [InlineKeyboardButton("Car 🚗", callback_data="car"),
         InlineKeyboardButton("Public Transport 🚌", callback_data="public_transport"),
         InlineKeyboardButton("Bicycle 🚲", callback_data="bicycle"),
         InlineKeyboardButton("Walking 🚶‍♂️", callback_data="walking")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply(text, reply_markup=reply_markup)


async def help_command(message: types.Message):
    help_text = "To use this bot, simply select your transportation mode and follow the instructions provided."
    help_text += " You can also use the following commands:\n"
    help_text += "/start - Start the bot and select transportation mode.\n"
    help_text += "/help - Show help information.\n"
    help_text += "/statistics - Show your carbon footprint statistics.\n"
    help_text += "/reset - Reset your carbon footprint data."
    await message.reply(help_text)


async def format_statistics(user_data, time_period=None):
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


async def statistics(message: types.Message):
    time_period = None
    async with bot.data_proxy() as user_data:
        if 'period' in user_data:
            time_period = user_data['period']

        text = await format_statistics(user_data, time_period)
        await message.reply(text)


async def store_transportation_data(user_data, mode, distance):
    emission = distance * EMISSION_FACTORS[mode]
    user_data['footprint'] += emission
    user_data['history'].append({
        'mode': mode,
        'distance': distance,
        'emission': emission,
        'date': datetime.date.today().isoformat()
    })


async def update_achievements(user_data):
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


async def achievements(message: types.Message):
    async with bot.data_proxy() as user_data:
        achievements = user_data.get("achievements", [])
        if not achievements:
            await message.reply_text("You haven't earned any badges yet. Keep reducing your carbon footprint to unlock achievements!")
            return

        text = "🏆 Your Achievements:\n\n"
        for badge_id in achievements:
            badge = BADGES[badge_id]
            text += f"{badge['name']} - {badge['description']}\n"

        await message.reply(text)


async def share(message: types.Message):
    user = message.from_user
    async with bot.data_proxy() as user_data:
        achievements = user_data.get("achievements", [])
        if not achievements:
            await message.reply_text("You don't have any achievements to share yet.")
            return

        text = f"{user.first_name} has been using the Carbon Footprint Calculator bot and has earned the following achievements:\n\n"
        for badge_id in achievements:
            badge = BADGES[badge_id]
            text += f"{badge['name']} - {badge['description']}\n"

        text += "\nJoin the carbon footprint reduction journey using the Carbon Footprint Calculator bot: https://t.me/Habitr_bot"
        await message.reply(text)


async def reset(message: types.Message):
    async with bot.data_proxy() as user_data:
        user_data['footprint'] = 0
        user_data['history'] = []
    await message.reply_text("Your carbon footprint data has been reset.")


async def mode_callback(query: CallbackQuery):
    mode = query.data
    async with FSMContext(user_id=query.from_user.id, chat_id=query.message.chat.id) as state:
        await state.update_data(mode=mode)
        await Form.distance.set()
        await query.answer()
        await query.message.reply("Enter the distance in km:", reply_markup=types.ReplyKeyboardRemove())


async def distance_callback(message: types.Message, state: FSMContext):
    distance = float(message.text)
    async with state.proxy() as data:
        mode = data['mode']
    await store_transportation_data

async def distance_callback(message: types.Message, state: FSMContext):
    distance = float(message.text)
    async with state.proxy() as data:
        mode = data['mode']
    async with bot.data_proxy() as user_data:
        await store_transportation_data(user_data, mode, distance)
        await state.finish()
        badge_message = await update_achievements(user_data)
        if badge_message:
            await message.answer(badge_message)
        await message.answer("Thank you for your submission! Your carbon footprint has been updated.")

if __name__ == '__main__':
    # Commands
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(help_command, commands=['help'])
    dp.register_message_handler(statistics, commands=['statistics'])
    dp.register_message_handler(achievements, commands=['achievements'])
    dp.register_message_handler(share, commands=['share'])
    dp.register_message_handler(reset, commands=['reset'])

    # Callbacks
    dp.register_callback_query_handler(mode_callback, lambda query: query.data in EMISSION_FACTORS.keys())
    dp.register_message_handler(distance_callback, state=Form.distance)

    # Start the bot
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    try:
        loop.run_forever()
    finally:
        loop.stop()
