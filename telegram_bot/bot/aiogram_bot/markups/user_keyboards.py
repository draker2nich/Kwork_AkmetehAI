from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.requests import products as db
from bot.texts import START_TEXT


async def build_user_category_keyboard(current_category_id: int | None = None):
    """Строит клавиатуру для навигации пользователя по категориям и товарам."""
    builder = InlineKeyboardBuilder()

    if current_category_id is None:
        categories = await db.get_root_categories()
        # Используем START_TEXT вместо "Привет! Что ищем сегодня?"
        header_text = START_TEXT
    else:
        categories = await db.get_subcategories(current_category_id)
        current_cat = await db.get_category_by_id(current_category_id)
        header_text = current_cat.prompt_text if current_cat.prompt_text else f"📂 <b>{current_cat.name}</b>"

    for cat in categories:
        builder.button(text=f"📁 {cat.name}", callback_data=f"user_cat_{cat.id}")

    builder.adjust(1)

    # Filter button
    filter_cb = f"user_filter_{current_category_id if current_category_id else 'root'}"
    builder.row(types.InlineKeyboardButton(text="🔍 Фильтр", callback_data=filter_cb))

    if current_category_id is not None:
        parent = (await db.get_category_by_id(current_category_id)).parent_id
        back_cb = f"user_cat_{parent}" if parent else "user_cat_root"
        builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))

    return builder.as_markup(), header_text


def get_back_to_category_keyboard(category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ К списку", callback_data=f"user_cat_{category_id}")
    return builder.as_markup()


def get_filter_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 PDF / Документы", callback_data="set_filter_document")
    builder.button(text="🎥 Видео", callback_data="set_filter_video")
    builder.button(text="📝 Текст", callback_data="set_filter_text")
    builder.button(text="❌ Без фильтра", callback_data="set_filter_none")
    builder.adjust(1)
    return builder.as_markup()