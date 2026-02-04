import json
import logging
from typing import List

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.serialization import deserialize_telegram_object_to_python

from bot.aiogram_bot.markups.keyboards import admin_keyboard, mass_mail_keyboard, back_keyboard
from bot.aiogram_bot.misc.media_utils import copy_post
from bot.aiogram_bot.misc.states import MassSend
from bot.database.models import User
from bot.database.requests.users import get_user_ids
from bot.texts import MASS_SEND_BTN
from bot.texts import OK_BTN, ADMIN_WAIT_MASS_MSG_TEXT, ADMIN_CHECK_POST_TEXT, \
    ADMIN_MASS_MAIL_START_TEXT, ADMIN_MASS_MAIL_END_TEXT

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == MASS_SEND_BTN)
async def mass_send(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(ADMIN_WAIT_MASS_MSG_TEXT,
                         reply_markup=back_keyboard)
    await state.set_state(MassSend.msg)


@router.message(MassSend.msg)
async def send_users_2(message: types.Message, state: FSMContext, user: User, album: List[types.Message] = None):
    await copy_post(album or message, user.user_id, message.bot)
    await message.answer(ADMIN_CHECK_POST_TEXT, reply_markup=mass_mail_keyboard)
    json_album = [json.dumps(deserialize_telegram_object_to_python(m)) for m in album] if album else None
    json_msg = json.dumps(deserialize_telegram_object_to_python(message))
    await state.update_data(json_album=json_album, json_msg=json_msg)
    await state.set_state(MassSend.confirmation)


@router.message(MassSend.confirmation, F.text == OK_BTN)
async def send_users_3(message: types.Message, state: FSMContext):
    users = await get_user_ids()
    data = await state.get_data()
    await state.clear()
    waitmsg = await message.answer(ADMIN_MASS_MAIL_START_TEXT.format(str(len(users))), reply_markup=admin_keyboard)
    album = [types.Message.model_validate(json.loads(m)) for m in data.get("json_album")] if data.get(
        "json_album") else None
    msg = types.Message.model_validate(json.loads(data.get("json_msg"))) if data.get("json_msg") else None
    for user_ in users:
        try:
            await copy_post(album or msg, user_, message.bot)
        except Exception as e:
            continue
    await waitmsg.reply(ADMIN_MASS_MAIL_END_TEXT)
