import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.user_keyboards import (
    build_user_category_keyboard,
    get_back_to_category_keyboard,
    get_filter_selection_keyboard
)
from bot.database.requests import products as db
from bot.utils.item_sender import send_item_content

router = Router()
logger = logging.getLogger(__name__)


# УДАЛЕНО: хендлер @router.message(F.text == "🗂 Каталог") - больше не нужен


@router.callback_query(F.data == "user_cat_root")
async def nav_user_root(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"User {callback.from_user.id} navigated to root category")
    await state.update_data(active_filter=None)
    kb, text = await build_user_category_keyboard(None)
    
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("user_cat_"))
async def nav_user_category(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    logger.info(f"User {callback.from_user.id} navigated to category {cat_id}")
    await show_category(callback.message, cat_id, state)


@router.callback_query(F.data.startswith("user_filter_"))
async def open_filter_menu(callback: types.CallbackQuery, state: FSMContext):
    cat_data = callback.data.split("_")[2]
    cat_id = int(cat_data) if cat_data != 'root' else None
    
    logger.info(f"User {callback.from_user.id} opened filter menu for category {cat_id}")
    await state.update_data(filter_category_id=cat_id)
    
    await callback.message.edit_text("Выберите тип материалов для фильтрации:",
                                     reply_markup=get_filter_selection_keyboard())


@router.callback_query(F.data.startswith("set_filter_"))
async def set_filter(callback: types.CallbackQuery, state: FSMContext):
    filter_type = callback.data.split("_")[2]
    
    logger.info(f"User {callback.from_user.id} set filter: {filter_type}")
    if filter_type == "none":
        await state.update_data(active_filter=None)
    else:
        await state.update_data(active_filter=filter_type)

    data = await state.get_data()
    cat_id = data.get("filter_category_id")

    await show_category(callback.message, cat_id, state)


async def show_category(message: types.Message, cat_id: int | None, state: FSMContext, edit: bool = True):
    data = await state.get_data()
    active_filter = data.get("active_filter")

    kb, text = await build_user_category_keyboard(cat_id)

    if active_filter:
        filter_name = {
            "document": "PDF / Документы",
            "video": "Видео",
            "text": "Текст"
        }.get(active_filter, active_filter)
        text += f"\n\n🔍 Фильтр: <b>{filter_name}</b>"

    items = await db.get_items_by_category(cat_id)

    if items and active_filter:
        items = [i for i in items if i.content_type == active_filter]

    if items:
        try:
            await message.delete()
        except Exception:
            pass

        await message.answer("Вот что я нашёл 👇")

        for item in items:
            caption = f"<b>{item.name}</b>"
            if item.description:
                caption += f"\n\n{item.description}"

            await send_item_content(message, item, caption)

        await message.answer("Выберите действие 👇", reply_markup=kb)
    else:
        if edit:
            try:
                await message.edit_text(text, reply_markup=kb)
            except Exception:
                await message.answer(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("user_item_"))
async def view_item(callback: types.CallbackQuery):
    """Показывает/отправляет товар пользователю"""
    item_id = int(callback.data.split("_")[2])
    logger.info(f"User {callback.from_user.id} viewing item {item_id}")
    item = await db.get_item_by_id(item_id)

    caption = f"<b>{item.name}</b>"
    if item.description:
        caption += f"\n\n{item.description}"

    kb = get_back_to_category_keyboard(item.category_id)

    await callback.message.delete()

    await send_item_content(callback.message, item, caption, reply_markup=kb)