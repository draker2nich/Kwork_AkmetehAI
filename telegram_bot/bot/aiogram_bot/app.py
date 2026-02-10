import logging

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from bot.aiogram_bot.misc.middlewares import register_middlewares
from bot.aiogram_bot.misc.middlewares.admin_middleware import IsAdminMiddleware
from bot.database.models import on_startup_database
from bot.utils.config import settings


async def aiogram_on_startup(bot: Bot):
    await on_startup_database()

    bot_info = await bot.get_me()
    logging.info("Bot has been started! -> @" + str(bot_info.username))


def register_routers(dp: Dispatcher):
    from bot.aiogram_bot.handlers.users import menu, view, any
    from bot.aiogram_bot.handlers.admins import join, mass_send, stats, items_management
    
    # Публичный роутер для /admin (без admin middleware)
    dp.include_router(join.public_router)
    
    dp.include_routers(
        menu.router,
        view.router,
    )

    admin_routers = [
        join.router,
        mass_send.router,
        stats.router,
        items_management.router,
    ]

    if admin_routers:
        for admin_router in admin_routers:
            admin_router.message.middleware(IsAdminMiddleware())
            admin_router.callback_query.middleware(IsAdminMiddleware())
        dp.include_routers(*admin_routers)

    dp.include_routers(
        any.router,
    )

async def aiogram_start():
    bot = Bot(token=settings.TG_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    if not settings.REDIS_URL:
        storage = MemoryStorage()
    else:
        storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage, parse_mode='HTML')

    register_middlewares(dp)
    register_routers(dp)
    await aiogram_on_startup(bot)
    await dp.start_polling(bot)
