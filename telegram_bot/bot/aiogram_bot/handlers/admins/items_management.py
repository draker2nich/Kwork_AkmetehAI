import logging
import os

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.aiogram_bot.markups.admin_keyboards import (
    get_back_keyboard,
    build_category_keyboard,
    get_item_details_keyboard,
    get_skip_keyboard,
)
from bot.aiogram_bot.misc.states import AdminState
from bot.database.requests import products as db
from bot.utils.item_sender import send_item_content

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "Управление предметами")
async def start_items_management(message: types.Message, state: FSMContext):
    logger.info(f"Admin {message.from_user.id} started items management")
    await state.update_data(filter_type=None)
    kb, text = await build_category_keyboard(None)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: types.CallbackQuery):
    await callback.answer()


# ── Sort: categories ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sort_cat_up_"))
async def sort_category_up(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[3])
    category = await db.get_category_by_id(cat_id)
    moved = await db.move_category(cat_id, "up")
    if not moved:
        await callback.answer("Невозможно переместить")
        return
    await callback.answer("Перемещено вверх")
    parent_id = category.parent_id if category else None
    kb, text = await build_category_keyboard(parent_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'Error: {e}')


@router.callback_query(F.data.startswith("sort_cat_down_"))
async def sort_category_down(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[3])
    category = await db.get_category_by_id(cat_id)
    moved = await db.move_category(cat_id, "down")
    if not moved:
        await callback.answer("Невозможно переместить")
        return
    await callback.answer("Перемещено вниз")
    parent_id = category.parent_id if category else None
    kb, text = await build_category_keyboard(parent_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'Error: {e}')


@router.callback_query(F.data.startswith("sort_cat_swap_"))
async def sort_category_swap(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    left_id, right_id = int(parts[3]), int(parts[4])
    moved = await db.swap_elements(left_id, right_id, is_category=True)
    if not moved:
        await callback.answer("Невозможно переместить")
        return
    await callback.answer("Поменяли местами")
    cat = await db.get_category_by_id(left_id)
    parent_id = cat.parent_id if cat else None
    kb, text = await build_category_keyboard(parent_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'Error: {e}')


# ── Sort: items ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sort_item_up_"))
async def sort_item_up(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[3])
    item = await db.get_item_by_id(item_id)
    moved = await db.move_item(item_id, "up")
    if not moved:
        await callback.answer("Невозможно переместить")
        return
    await callback.answer("Перемещено вверх")
    kb, text = await build_category_keyboard(item.category_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'Error: {e}')


@router.callback_query(F.data.startswith("sort_item_down_"))
async def sort_item_down(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[3])
    item = await db.get_item_by_id(item_id)
    moved = await db.move_item(item_id, "down")
    if not moved:
        await callback.answer("Невозможно переместить")
        return
    await callback.answer("Перемещено вниз")
    kb, text = await build_category_keyboard(item.category_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'Error: {e}')


@router.callback_query(F.data.startswith("sort_item_swap_"))
async def sort_item_swap(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    left_id, right_id = int(parts[3]), int(parts[4])
    moved = await db.swap_elements(left_id, right_id, is_category=False)
    if not moved:
        await callback.answer("Невозможно переместить")
        return
    await callback.answer("Поменяли местами")
    item = await db.get_item_by_id(left_id)
    kb, text = await build_category_keyboard(item.category_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'Error: {e}')


# ── Navigation ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "nav_cat_root")
async def nav_root(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(last_category_id=None)
    kb, text = await build_category_keyboard(None)
    try:
        if callback.message.content_type == "text":
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'error - {e}')
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("nav_cat_"))
async def nav_category(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    await state.update_data(last_category_id=cat_id)
    kb, text = await build_category_keyboard(cat_id)
    try:
        if callback.message.content_type == "text":
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb)
    except Exception as e:
        logger.exception(f'error - {e}')
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("nav_item_"))
async def nav_item_details(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    item = await db.get_item_by_id(item_id)
    caption = f"<b>Предмет: {item.name}</b>\n"
    if item.description:
        caption += f"\nОписание: {item.description}"
    caption += f"\nТип: {item.content_type}"
    kb = get_item_details_keyboard(item.id, item.category_id)
    await callback.message.delete()
    await send_item_content(callback.message, item, caption, reply_markup=kb)


# ── Edit category ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_cat_name_"))
async def edit_category_name_handler(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[3])
    category = await db.get_category_by_id(cat_id)
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminState.waiting_for_new_category_name)
    back_cb = f"nav_cat_{cat_id}"
    await callback.message.edit_text(
        f"Текущее название: <b>{category.name}</b>\n\nВведите новое название категории:",
        reply_markup=get_back_keyboard(back_cb)
    )


@router.message(AdminState.waiting_for_new_category_name)
async def process_new_category_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст.")
        return
    data = await state.get_data()
    cat_id = data.get("category_id")
    new_name = message.text.strip()
    await db.update_category(cat_id, name=new_name)
    kb, text = await build_category_keyboard(cat_id)
    await message.answer(f"Название категории изменено на: <b>{new_name}</b>\n\n{text}", reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("edit_prompt_"))
async def edit_prompt_handler(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    category = await db.get_category_by_id(cat_id)
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminState.waiting_for_new_prompt)
    back_cb = f"nav_cat_{cat_id}"
    current_prompt = category.prompt_text or "(не задан)"
    await callback.message.edit_text(
        f"Текущий текст:\n<blockquote>{current_prompt}</blockquote>\n\nВведите новый текст:",
        reply_markup=get_back_keyboard(back_cb)
    )


@router.message(AdminState.waiting_for_new_prompt)
async def process_new_prompt(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст.")
        return
    data = await state.get_data()
    cat_id = data.get("category_id")
    new_prompt = message.text
    await db.update_category(cat_id, prompt_text=new_prompt)
    kb, text = await build_category_keyboard(cat_id)
    await message.answer(f"Текст обновлен!\n\n{text}", reply_markup=kb)
    await state.clear()


# ── Edit item ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_item_name_"))
async def edit_item_name_handler(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[3])
    item = await db.get_item_by_id(item_id)
    await state.update_data(item_id=item_id, category_id=item.category_id)
    await state.set_state(AdminState.waiting_for_new_item_name)
    back_cb = f"nav_item_{item_id}"
    await callback.message.answer(
        f"Текущее название: <b>{item.name}</b>\n\nВведите новое название:",
        reply_markup=get_back_keyboard(back_cb)
    )


@router.message(AdminState.waiting_for_new_item_name)
async def process_new_item_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст.")
        return
    data = await state.get_data()
    item_id = data.get("item_id")
    new_name = message.text.strip()
    await db.update_item(item_id, name=new_name)
    item = await db.get_item_by_id(item_id)
    caption = f"<b>Предмет: {item.name}</b>\n"
    if item.description:
        caption += f"\nОписание: {item.description}"
    caption += f"\nТип: {item.content_type}"
    kb = get_item_details_keyboard(item.id, item.category_id)
    await message.answer(f"Название изменено на: <b>{new_name}</b>")
    await send_item_content(message, item, caption, reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("edit_item_desc_"))
async def edit_item_desc_handler(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[3])
    item = await db.get_item_by_id(item_id)
    await state.update_data(item_id=item_id, category_id=item.category_id)
    await state.set_state(AdminState.waiting_for_new_item_desc)
    back_cb = f"nav_item_{item_id}"
    current_desc = item.description or "(не задано)"
    await callback.message.answer(
        f"Текущее описание:\n<blockquote>{current_desc}</blockquote>\n\nВведите новое описание (или '-' чтобы удалить):",
        reply_markup=get_back_keyboard(back_cb)
    )


@router.message(AdminState.waiting_for_new_item_desc)
async def process_new_item_desc(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст.")
        return
    data = await state.get_data()
    item_id = data.get("item_id")
    new_desc = message.text.strip()
    if new_desc == "-":
        new_desc = None
    await db.update_item(item_id, description=new_desc)
    item = await db.get_item_by_id(item_id)
    caption = f"<b>Предмет: {item.name}</b>\n"
    if item.description:
        caption += f"\nОписание: {item.description}"
    caption += f"\nТип: {item.content_type}"
    kb = get_item_details_keyboard(item.id, item.category_id)
    await message.answer("Описание обновлено!")
    await send_item_content(message, item, caption, reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("edit_item_file_"))
async def edit_item_file_handler(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[3])
    item = await db.get_item_by_id(item_id)
    await state.update_data(item_id=item_id, category_id=item.category_id)
    await state.set_state(AdminState.waiting_for_new_item_file)
    back_cb = f"nav_item_{item_id}"
    await callback.message.answer(
        f"Отправьте новый файл для предмета <b>{item.name}</b>:",
        reply_markup=get_back_keyboard(back_cb)
    )


@router.message(AdminState.waiting_for_new_item_file)
async def process_new_item_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item_id = data.get("item_id")
    category_id = data.get("category_id")
    item = await db.get_item_by_id(item_id)

    content_type = None
    file_id = None
    original_filename = None

    if message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        original_filename = message.video.file_name
    elif message.document:
        file_id = message.document.file_id
        original_filename = message.document.file_name
        if original_filename and original_filename.lower().endswith('.pptx'):
            content_type = "pptx"
        else:
            content_type = "document"
    else:
        await message.answer("Неподдерживаемый тип файла.")
        return

    if item.file_path and os.path.exists(item.file_path):
        try:
            os.remove(item.file_path)
        except Exception as e:
            logger.error(f"Error deleting old file {item.file_path}: {e}")

    bot = message.bot
    file_info = await bot.get_file(file_id)
    category_path_list = await db.get_category_full_path(category_id)
    sanitized_path_list = ["".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip() for name in category_path_list]
    category_path_str = os.path.join(*sanitized_path_list) if sanitized_path_list else "root"
    save_dir = os.path.join("files", category_path_str)
    os.makedirs(save_dir, exist_ok=True)

    if not original_filename:
        ext = file_info.file_path.split('.')[-1]
        safe_name = "".join(c for c in item.name if c.isalnum() or c in (' ', '_', '-')).strip()
        original_filename = f"{safe_name}.{ext}"

    safe_filename = "".join(c for c in original_filename if c.isalnum() or c in (' ', '_', '-', '.')).strip()
    file_path = os.path.join(save_dir, safe_filename)

    counter = 1
    base_name, extension = os.path.splitext(safe_filename)
    while os.path.exists(file_path):
        file_path = os.path.join(save_dir, f"{base_name}_{counter}{extension}")
        counter += 1

    await bot.download_file(file_info.file_path, file_path)
    await db.update_item(item_id, content_type=content_type, file_id=file_id, file_path=file_path)

    item = await db.get_item_by_id(item_id)
    caption = f"<b>Предмет: {item.name}</b>\n"
    if item.description:
        caption += f"\nОписание: {item.description}"
    caption += f"\nТип: {item.content_type}"
    kb = get_item_details_keyboard(item.id, item.category_id)
    await message.answer("Файл заменен!")
    await send_item_content(message, item, caption, reply_markup=kb)
    await state.clear()


# ── Add category ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_cat_"))
async def start_add_category(callback: types.CallbackQuery, state: FSMContext):
    data_part = callback.data.split("_")[2]
    parent_id = int(data_part) if data_part != "root" else None
    await state.update_data(parent_id=parent_id)
    await state.set_state(AdminState.waiting_for_category_name)
    back_cb = f"nav_cat_{parent_id}" if parent_id else "nav_cat_root"
    await callback.message.edit_text("Введите название новой категории:", reply_markup=get_back_keyboard(back_cb))
    await callback.answer()


@router.message(AdminState.waiting_for_category_name)
async def process_category_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое название.")
        return
    await state.update_data(name=message.text)
    await state.set_state(AdminState.waiting_for_category_prompt)
    await message.answer("Введите текст для этой категории:",
                         reply_markup=get_skip_keyboard("add_cat_skip_prompt", "add_cat_back_to_name"))


@router.callback_query(F.data == "add_cat_back_to_name")
async def back_to_category_name(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    parent_id = data.get("parent_id")
    back_cb = f"nav_cat_{parent_id}" if parent_id else "nav_cat_root"
    await state.set_state(AdminState.waiting_for_category_name)
    await callback.message.edit_text("Введите название новой категории:", reply_markup=get_back_keyboard(back_cb))


@router.callback_query(F.data == "add_cat_skip_prompt")
async def skip_category_prompt(callback: types.CallbackQuery, state: FSMContext):
    await finish_add_category(callback, state, None)


@router.message(AdminState.waiting_for_category_prompt)
async def process_category_prompt(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст")
        return
    await finish_add_category(message, state, message.text)


async def finish_add_category(event, state: FSMContext, prompt_text: str | None):
    data = await state.get_data()
    parent_id = data.get("parent_id")
    name = data.get("name")
    message = event.message if isinstance(event, types.CallbackQuery) else event
    await db.add_category(name=name, parent_id=parent_id, prompt_text=prompt_text)
    kb, text = await build_category_keyboard(parent_id)
    await message.answer(f"Категория '{name}' создана!\n\n{text}", reply_markup=kb)
    await state.clear()


# ── Delete ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("del_cat_"))
async def delete_category_handler(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[2])
    category = await db.get_category_by_id(cat_id)
    parent_id = category.parent_id
    await db.delete_category(cat_id)
    await callback.answer("Категория удалена", show_alert=True)
    kb, text = await build_category_keyboard(parent_id)
    try:
        if callback.message.content_type == "text":
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("del_item_"))
async def delete_item_handler(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    item = await db.get_item_by_id(item_id)
    cat_id = item.category_id
    if item.file_path and os.path.exists(item.file_path):
        try:
            os.remove(item.file_path)
        except Exception as e:
            logger.error(f"Error deleting file {item.file_path}: {e}")
    await db.delete_item(item_id)
    await callback.answer("Предмет удален", show_alert=True)
    kb, text = await build_category_keyboard(cat_id)
    try:
        if callback.message.content_type == "text":
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# ── Add item ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_item_"))
async def start_add_item(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminState.waiting_for_item_name)
    await callback.message.edit_text("Введите название предмета:",
                                     reply_markup=get_back_keyboard(f"nav_cat_{cat_id}"))
    await callback.answer()


@router.callback_query(F.data == "add_item_back_to_name")
async def back_to_item_name(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get("category_id")
    await state.set_state(AdminState.waiting_for_item_name)
    await callback.message.edit_text("Введите название предмета:",
                                     reply_markup=get_back_keyboard(f"nav_cat_{cat_id}"))


@router.message(AdminState.waiting_for_item_name)
async def item_name_entered(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое название.",
                             reply_markup=get_back_keyboard("add_item_back_to_name"))
        return
    await state.update_data(name=message.text)
    await state.set_state(AdminState.waiting_for_item_content)
    await message.answer("Отправьте контент предмета:", reply_markup=get_back_keyboard("add_item_back_to_name"))


@router.message(AdminState.waiting_for_item_content)
async def item_content_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    content_type = "text"
    file_id = None
    original_filename = None
    description = message.caption or message.text

    if message.text:
        content_type = "text"
    elif message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        original_filename = message.video.file_name
    elif message.document:
        file_id = message.document.file_id
        original_filename = message.document.file_name
        if original_filename and original_filename.lower().endswith('.pptx'):
            content_type = "pptx"
        else:
            content_type = "document"
    else:
        await message.answer("Неподдерживаемый тип контента.",
                             reply_markup=get_back_keyboard("add_item_back_to_name"))
        return

    if content_type == "text":
        item = await db.add_item(
            name=data['name'], category_id=data['category_id'],
            content_type="text", description=description
        )
        await message.answer(f"Предмет <b>{item.name}</b> (Текст) успешно добавлен!")
        kb, text = await build_category_keyboard(data['category_id'])
        await message.answer(text, reply_markup=kb)
        await state.clear()
        return

    bot = message.bot
    file_info = await bot.get_file(file_id)
    category_path_list = await db.get_category_full_path(data['category_id'])
    sanitized_path_list = ["".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip() for name in category_path_list]
    category_path_str = os.path.join(*sanitized_path_list) if sanitized_path_list else "root"
    save_dir = os.path.join("files", category_path_str)
    os.makedirs(save_dir, exist_ok=True)

    if not original_filename:
        ext = file_info.file_path.split('.')[-1]
        safe_name = "".join(c for c in data['name'] if c.isalnum() or c in (' ', '_', '-')).strip()
        original_filename = f"{safe_name}.{ext}"

    safe_filename = "".join(c for c in original_filename if c.isalnum() or c in (' ', '_', '-', '.')).strip()
    file_path = os.path.join(save_dir, safe_filename)

    counter = 1
    base_name, extension = os.path.splitext(safe_filename)
    while os.path.exists(file_path):
        file_path = os.path.join(save_dir, f"{base_name}_{counter}{extension}")
        counter += 1

    await bot.download_file(file_info.file_path, file_path)
    item = await db.add_item(
        name=data['name'], category_id=data['category_id'],
        content_type=content_type, description=description,
        file_id=file_id, file_path=file_path
    )
    await message.answer(f"Предмет <b>{item.name}</b> успешно добавлен!")
    kb, text = await build_category_keyboard(data['category_id'])
    await message.answer(text, reply_markup=kb)
    await state.clear()