import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.keyboards import get_main_keyboard
from bot.aiogram_bot.markups.user_keyboards import build_user_category_keyboard
from bot.database.models import User
from bot.texts import BACK_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith("/start"))
async def start_btn(message: types.Message, state: FSMContext, user: User):
    """При /start сразу показываем категории с inline-кнопками"""
    await state.clear()
    await state.update_data(active_filter=None)
    
    kb, text = await build_user_category_keyboard(None)
    
    await message.bot.send_message(
        user.user_id,
        text=text,
        reply_markup=kb,
    )
    
    main_kb = get_main_keyboard(user)
    if main_kb and not isinstance(main_kb, types.ReplyKeyboardRemove):
        pass


@router.message(F.text == BACK_BTN)
async def back_btn(message: types.Message, state: FSMContext, user: User):
    """Кнопка назад - возвращает к корневым категориям (только для обычных пользователей)"""
    # Проверяем, не находится ли пользователь в каком-либо состоянии админки
    # Если состояние уже очищено другим хендлером - просто показываем меню
    current_state = await state.get_state()
    
    # Очищаем состояние
    await state.clear()
    await state.update_data(active_filter=None)
    
    kb, text = await build_user_category_keyboard(None)
    
    await message.bot.send_message(
        user.user_id,
        text=text,
        reply_markup=kb,
    )