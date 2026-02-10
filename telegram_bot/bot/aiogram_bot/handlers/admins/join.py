import logging

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.keyboards import admin_keyboard
from bot.aiogram_bot.markups.admin_keyboards import build_category_keyboard
from bot.texts import ADMIN_BTN, START_TEXT
from bot.utils.config import settings

router = Router()
public_router = Router()
logger = logging.getLogger(__name__)


@public_router.message(Command("admin"))
async def admin_command(message: types.Message, state: FSMContext):
    """Обработчик команды /admin для всех пользователей"""
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("У вас нет прав доступа к админ-панели")
        return
    
    await state.clear()
    await state.update_data(filter_type=None)
    
    # Сначала устанавливаем reply-клавиатуру админа
    await message.answer("Админ-панель", reply_markup=admin_keyboard)
    
    # Затем показываем inline-кнопки с категориями
    kb, text = await build_category_keyboard(None)
    await message.answer(START_TEXT, reply_markup=kb)


@router.message(F.text == ADMIN_BTN)
async def admin_join(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(filter_type=None)
    
    kb, text = await build_category_keyboard(None)
    await message.answer(START_TEXT, reply_markup=kb)