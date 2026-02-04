import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.keyboards import get_main_keyboard
from bot.database.models import User
from bot.texts import BACK_BTN, START_TEXT

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith("/start"))
@router.message(F.text == BACK_BTN)
async def start_btn(message: types.Message, state: FSMContext, user: User):
    await state.clear()
    return await message.bot.send_message(
        user.user_id,
        text=START_TEXT,
        reply_markup=get_main_keyboard(user),
    )
