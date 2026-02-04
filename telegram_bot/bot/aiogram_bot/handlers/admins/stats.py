import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.database.requests.users import get_user_stats
from bot.texts import STATS_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == STATS_BTN)
async def stats_btn(message: types.Message, state: FSMContext):
    stats = await get_user_stats()

    text = (
        "📈 <b>Статистика</b>\n\n"
        "<blockquote>"
        "Всего пользователей: {total}\n\n"
        "Пользователей за 24ч/3д/7д/30д: {n24}/{n3}/{n7}/{n30}\n\n"
        "Активных пользователей за 24ч/3д/7д/30д: {a24}/{a3}/{a7}/{a30}"
        "</blockquote>"
    ).format(
        total=stats["total_users"],
        n24=stats["new_users_24h"],
        n3=stats["new_users_3d"],
        n7=stats["new_users_7d"],
        n30=stats["new_users_30d"],
        a24=stats["active_users_24h"],
        a3=stats["active_users_3d"],
        a7=stats["active_users_7d"],
        a30=stats["active_users_30d"],
    )

    await message.answer(text)
