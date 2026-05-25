import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Добавьте переменную окружения BOT_TOKEN")

dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("🎰 БОТ РАБОТАЕТ! Добро пожаловать в Казино ХС!")

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("🎰 БОТ ЗАПУЩЕН!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())