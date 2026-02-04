from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.keyboards import get_main_keyboard
from bot.database.models import User
from bot.texts import ANY_TEXT

router = Router()


@router.message()
async def any_message(message: types.Message, state: FSMContext, user: User):
    await state.clear()
    return await message.bot.send_message(user.user_id, text=ANY_TEXT, reply_markup=get_main_keyboard(user))


@router.callback_query()
async def any_callback(call: types.CallbackQuery, state: FSMContext, user: User):
    await state.clear()
    return await call.bot.send_message(user.user_id, text=ANY_TEXT, reply_markup=get_main_keyboard(user))
