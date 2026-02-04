import asyncio

from bot.aiogram_bot.app import aiogram_start
from bot.utils.logger import setup_logging

if __name__ == '__main__':
    try:
        setup_logging()
        asyncio.run(aiogram_start())
    except KeyboardInterrupt:
        print("Goodbye!")
