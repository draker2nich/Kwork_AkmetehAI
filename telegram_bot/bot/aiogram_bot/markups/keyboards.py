from aiogram import types

from bot.database.models import User
from bot.texts import (
    ADMIN_BTN,
    BACK_BTN,
    STATS_BTN,
    MASS_SEND_BTN,
    OK_BTN,
)
from bot.utils.config import settings


def get_main_keyboard(user: User) -> types.ReplyKeyboardMarkup:
    kbd = []
    if user.user_id in settings.ADMIN_IDS:
        kbd.append([types.KeyboardButton(text=ADMIN_BTN)])
    if not kbd:
        return types.ReplyKeyboardRemove()
    return types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=kbd)


def get_admin_keyboard(user: User) -> types.ReplyKeyboardMarkup:
    keyboard: list[list[types.KeyboardButton]] = []
    if user.user_id in settings.ADMIN_IDS:
        keyboard.append([types.KeyboardButton(text=ADMIN_BTN)])
    return types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard)


admin_keyboard = types.ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [types.KeyboardButton(text="Управление предметами")],
        [types.KeyboardButton(text=MASS_SEND_BTN)],
        [types.KeyboardButton(text=STATS_BTN)],
        [types.KeyboardButton(text=BACK_BTN)],
    ],
)

mass_mail_keyboard = types.ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [types.KeyboardButton(text=OK_BTN)],
        [types.KeyboardButton(text=BACK_BTN)],
    ],
)

back_keyboard = types.ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [types.KeyboardButton(text=BACK_BTN)],
    ],
)