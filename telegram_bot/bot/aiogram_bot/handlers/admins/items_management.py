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


@router.message(F.text == "📦 Управление предметами")
async def start_items_management(message: types.Message, state: FSMContext):
    """Точка входа в админку предметов"""
    logger.info(f"Admin {message.from_user.id} started items management")
    await state.update_data(filter_type=None)
    
    kb, text = await build_category_keyboard(None)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "nav_cat_root")
async def nav_root(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"Admin {callback.from_user.id} navigated to root")
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
    logger.info(f"Admin {callback.from_user.id} navigated to category {cat_id}")
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
    logger.info(f"Admin {callback.from_user.id} viewing item {item_id}")
    item = await db.get_item_by_id(item_id)

    caption = f"📦 <b>Предмет: {item.name}</b>\n"
    if item.description:
        caption += f"\n📄 Описание: {item.description}"
    caption += f"\n📎 Тип: {item.content_type}"

    kb = get_item_details_keyboard(item.id, item.category_id)

    await callback.message.delete()

    await send_item_content(callback.message, item, caption, reply_markup=kb)


@router.callback_query(F.data.startswith("edit_prompt_"))
async def edit_prompt_handler(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminState.waiting_for_new_prompt)

    back_cb = f"nav_cat_{cat_id}"
    await callback.message.edit_text("✍️ Введите новый текст:", reply_markup=get_back_keyboard(back_cb))


@router.message(AdminState.waiting_for_new_prompt)
async def process_new_prompt(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текст.")
        return

    data = await state.get_data()
    cat_id = data.get("category_id")

    new_prompt = message.text
    
    logger.info(f"Admin {message.from_user.id} updating prompt for category {cat_id}")
    await db.update_category(cat_id, prompt_text=new_prompt)
    
    kb, text = await build_category_keyboard(cat_id)
    await message.answer(f"✅ Текст обновлен!\n\n{text}", reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("add_cat_"))
async def start_add_category(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")[2]
    parent_id = int(data) if data != "root" else None

    await state.update_data(parent_id=parent_id)
    await state.set_state(AdminState.waiting_for_category_name)

    back_cb = f"nav_cat_{parent_id}" if parent_id else "nav_cat_root"
    await callback.message.edit_text("✍️ Введите название новой категории:", reply_markup=get_back_keyboard(back_cb))
    await callback.answer()


@router.message(AdminState.waiting_for_category_name)
async def process_category_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое название.")
        return

    await state.update_data(name=message.text)
    await state.set_state(AdminState.waiting_for_category_prompt)

    # Determine back callback for the next step (back to name)
    # But back to name needs to know parent_id to render the 'Back' button of the name step correctly?
    # No, back_to_name handler handles that.

    await message.answer("✍️ Введите текст для этой категории:",
                         reply_markup=get_skip_keyboard("add_cat_skip_prompt", "add_cat_back_to_name"))


@router.callback_query(F.data == "add_cat_back_to_name")
async def back_to_category_name(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    parent_id = data.get("parent_id")
    back_cb = f"nav_cat_{parent_id}" if parent_id else "nav_cat_root"

    await state.set_state(AdminState.waiting_for_category_name)
    await callback.message.edit_text("✍️ Введите название новой категории:", reply_markup=get_back_keyboard(back_cb))


@router.callback_query(F.data == "add_cat_skip_prompt")
async def skip_category_prompt(callback: types.CallbackQuery, state: FSMContext):
    await finish_add_category(callback, state, None)


@router.message(AdminState.waiting_for_category_prompt)
async def process_category_prompt(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текст")
        return

    await finish_add_category(message, state, message.text)


async def finish_add_category(event, state: FSMContext, prompt_text: str | None):
    data = await state.get_data()
    parent_id = data.get("parent_id")
    name = data.get("name")

    # If event is CallbackQuery, use event.message
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    logger.info(f"Admin creating category '{name}' (parent_id={parent_id})")
    await db.add_category(name=name, parent_id=parent_id, prompt_text=prompt_text)
    
    kb, text = await build_category_keyboard(parent_id)
    await message.answer(f"✅ Категория '{name}' создана!\n\n{text}", reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("del_cat_"))
async def delete_category_handler(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[2])
    logger.info(f"Admin {callback.from_user.id} deleting category {cat_id}")
    category = await db.get_category_by_id(cat_id)
    parent_id = category.parent_id

    await db.delete_category(cat_id)

    await callback.answer("✅ Категория удалена", show_alert=True)

    if parent_id:
        kb, text = await build_category_keyboard(parent_id)
    else:
        kb, text = await build_category_keyboard(None)

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
    logger.info(f"Admin {callback.from_user.id} deleting item {item_id}")
    item = await db.get_item_by_id(item_id)
    cat_id = item.category_id

    if item.file_path and os.path.exists(item.file_path):
        try:
            os.remove(item.file_path)
        except Exception as e:
            logger.error(f"Error deleting file {item.file_path}: {e}")

    await db.delete_item(item_id)

    await callback.answer("✅ Предмет удален", show_alert=True)

    kb, text = await build_category_keyboard(cat_id)

    try:
        if callback.message.content_type == "text":
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("add_item_"))
async def start_add_item(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=cat_id)

    await state.set_state(AdminState.waiting_for_item_name)
    await callback.message.edit_text("📦 Введите название предмета:",
                                     reply_markup=get_back_keyboard(f"nav_cat_{cat_id}"))
    await callback.answer()


@router.callback_query(F.data == "add_item_back_to_name")
async def back_to_item_name(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get("category_id")

    await state.set_state(AdminState.waiting_for_item_name)
    await callback.message.edit_text("📦 Введите название предмета:",
                                     reply_markup=get_back_keyboard(f"nav_cat_{cat_id}"))


@router.message(AdminState.waiting_for_item_name)
async def item_name_entered(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое название.", reply_markup=get_back_keyboard("add_item_back_to_name"))
        return
    await state.update_data(name=message.text)
    await state.set_state(AdminState.waiting_for_item_content)
    await message.answer("📎 Отправьте контент предмета:", reply_markup=get_back_keyboard("add_item_back_to_name"))


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
        content_type = "document"
        file_id = message.document.file_id
        original_filename = message.document.file_name
    else:
        await message.answer("❌ Неподдерживаемый тип контента. Попробуйте снова.",
                             reply_markup=get_back_keyboard("add_item_back_to_name"))
        return

    if content_type == "text":
        logger.info(f"Admin adding text item '{data['name']}' to category {data['category_id']}")
        item = await db.add_item(
            name=data['name'],
            category_id=data['category_id'],
            content_type="text",
            description=description
        )
        await message.answer(f"✅ Предмет <b>{item.name}</b> (Текст) успешно добавлен!")

        kb, text = await build_category_keyboard(data['category_id'])
        await message.answer(text, reply_markup=kb)
        await state.clear()
        return

    # handle file
    bot = message.bot
    file_info = await bot.get_file(file_id)

    category_path_list = await db.get_category_full_path(data['category_id'])
    sanitized_path_list = ["".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip() for name in
                           category_path_list]
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
    
    logger.info(f"Admin adding file item '{data['name']}' to category {data['category_id']} (path={file_path})")
    item = await db.add_item(
        name=data['name'],
        category_id=data['category_id'],
        content_type=content_type,
        description=description,
        file_id=file_id,
        file_path=file_path
    )

    await message.answer(f"✅ Предмет <b>{item.name}</b> успешно добавлен! Файл сохранен.")

    kb, text = await build_category_keyboard(data['category_id'])
    await message.answer(text, reply_markup=kb)
    await state.clear()
