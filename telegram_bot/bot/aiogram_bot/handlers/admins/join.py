import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.keyboards import admin_keyboard
from bot.texts import ADMIN_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == ADMIN_BTN)
async def admin_join(message: types.Message, state: FSMContext):
    await message.answer("💻 <b>Вы в админ панели</b>", reply_markup=admin_keyboard)
