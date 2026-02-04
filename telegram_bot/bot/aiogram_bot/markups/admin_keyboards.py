from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.requests import products as db


async def build_category_keyboard(current_category_id: int | None = None):
    """Строит клавиатуру для навигации по категориям и предметам."""
    builder = InlineKeyboardBuilder()

    if current_category_id is None:
        categories = await db.get_root_categories()
        header_text = "📁 <b>Корневые категории</b>"
    else:
        categories = await db.get_subcategories(current_category_id)
        current_cat = await db.get_category_by_id(current_category_id)
        header_text = f"📂 Категория: <b>{current_cat.name}</b>"

    for cat in categories:
        builder.button(text=f"📁 {cat.name}", callback_data=f"nav_cat_{cat.id}")

    if current_category_id is not None:
        items = await db.get_items_by_category(current_category_id)
        for item in items:
            icon_map = {
                "text": "📝",
                "photo": "🖼",
                "video": "🎥",
                "document": "📄"
            }
            icon = icon_map.get(item.content_type, "📦")
            builder.button(text=f"{icon} {item.name}", callback_data=f"nav_item_{item.id}")

    builder.adjust(2)

    control_buttons = []

    cat_cb = f"add_cat_{current_category_id}" if current_category_id else "add_cat_root"
    control_buttons.append(types.InlineKeyboardButton(text="➕ Категорию", callback_data=cat_cb))

    if current_category_id is not None:
        control_buttons.append(
            types.InlineKeyboardButton(text="➕ Предмет", callback_data=f"add_item_{current_category_id}"))
        control_buttons.append(
            types.InlineKeyboardButton(text="✏️ Изм. текст", callback_data=f"edit_prompt_{current_category_id}"))
        control_buttons.append(
            types.InlineKeyboardButton(text="❌ Удалить эту категорию", callback_data=f"del_cat_{current_category_id}"))

        parent = (await db.get_category_by_id(current_category_id)).parent_id
        back_cb = f"nav_cat_{parent}" if parent else "nav_cat_root"
        control_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))

    builder.row(*control_buttons, width=2)

    return builder.as_markup(), header_text


def get_item_details_keyboard(item_id: int, category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить предмет", callback_data=f"del_item_{item_id}")
    builder.button(text="⬅️ К категории", callback_data=f"nav_cat_{category_id}")
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "admin_back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=callback_data)
    return builder.as_markup()


def get_skip_keyboard(skip_callback: str = "admin_skip", back_callback: str = "admin_back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Пропустить", callback_data=skip_callback)
    builder.button(text="⬅️ Назад", callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()
