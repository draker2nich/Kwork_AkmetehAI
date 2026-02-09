from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.requests import products as db


async def build_category_keyboard(current_category_id: int | None = None):
    """Строит клавиатуру для навигации по категориям и предметам.
    Элементы по 2 в ряд. Под каждой парой — кнопки сортировки.
    Поддерживается перемещение вверх/вниз/влево/вправо.
    """
    builder = InlineKeyboardBuilder()

    if current_category_id is None:
        categories = await db.get_root_categories()
        header_text = "<b>Корневые категории</b>"
    else:
        categories = await db.get_subcategories(current_category_id)
        current_cat = await db.get_category_by_id(current_category_id)
        header_text = f"Категория: <b>{current_cat.name}</b>"

    # Категории по 2 в ряд
    _add_grid_with_sort(builder, categories, prefix="cat", is_category=True)

    # Предметы
    if current_category_id is not None:
        items = await db.get_items_by_category(current_category_id)
        if categories and items:
            builder.row(types.InlineKeyboardButton(text="--- Предметы ---", callback_data="noop"))
        _add_grid_with_sort(builder, items, prefix="item", is_category=False)

    # Управляющие кнопки
    control_buttons = []
    cat_cb = f"add_cat_{current_category_id}" if current_category_id else "add_cat_root"
    control_buttons.append(types.InlineKeyboardButton(text="+ Категорию", callback_data=cat_cb))

    if current_category_id is not None:
        control_buttons.append(
            types.InlineKeyboardButton(text="+ Предмет", callback_data=f"add_item_{current_category_id}"))
        control_buttons.append(
            types.InlineKeyboardButton(text="Название", callback_data=f"edit_cat_name_{current_category_id}"))
        control_buttons.append(
            types.InlineKeyboardButton(text="Текст", callback_data=f"edit_prompt_{current_category_id}"))
        control_buttons.append(
            types.InlineKeyboardButton(text="Удалить категорию", callback_data=f"del_cat_{current_category_id}"))
        parent = (await db.get_category_by_id(current_category_id)).parent_id
        back_cb = f"nav_cat_{parent}" if parent else "nav_cat_root"
        control_buttons.append(types.InlineKeyboardButton(text="Назад", callback_data=back_cb))

    builder.row(*control_buttons, width=2)
    return builder.as_markup(), header_text


def _add_grid_with_sort(builder: InlineKeyboardBuilder, elements, prefix: str, is_category: bool):
    """Добавляет элементы по 2 в ряд с кнопками сортировки.
    
    Структура для пары:
    Ряд 1: [Элемент A] [Элемент B]
    Ряд 2: [⬆️A][⬇️A][swap_AB][⬆️B][⬇️B]
    
    Для нечётного последнего:
    Ряд 1: [Элемент]
    Ряд 2: [⬆️][⬇️]
    """
    total = len(elements)
    if total == 0:
        return

    for i in range(0, total, 2):
        left = elements[i]
        right = elements[i + 1] if i + 1 < total else None

        # Ряд с названиями
        if is_category:
            left_btn = types.InlineKeyboardButton(text=left.name, callback_data=f"nav_cat_{left.id}")
        else:
            left_btn = types.InlineKeyboardButton(text=_item_label(left), callback_data=f"nav_item_{left.id}")

        if right:
            if is_category:
                right_btn = types.InlineKeyboardButton(text=right.name, callback_data=f"nav_cat_{right.id}")
            else:
                right_btn = types.InlineKeyboardButton(text=_item_label(right), callback_data=f"nav_item_{right.id}")
            builder.row(left_btn, right_btn)
        else:
            builder.row(left_btn)

        # Ряд с кнопками сортировки
        sort_row = []
        cb = f"sort_{prefix}"

        # Левый элемент: вверх
        if i > 0:
            sort_row.append(types.InlineKeyboardButton(text="⬆️", callback_data=f"{cb}_up_{left.id}"))
        else:
            sort_row.append(types.InlineKeyboardButton(text=" ", callback_data="noop"))

        # Левый элемент: вниз
        if i < total - 1:
            sort_row.append(types.InlineKeyboardButton(text="⬇️", callback_data=f"{cb}_down_{left.id}"))
        else:
            sort_row.append(types.InlineKeyboardButton(text=" ", callback_data="noop"))

        if right:
            # Кнопка swap (поменять местами левый и правый)
            sort_row.append(types.InlineKeyboardButton(text="⇄", callback_data=f"{cb}_swap_{left.id}_{right.id}"))

            # Правый элемент: вверх
            if i + 1 > 0:
                sort_row.append(types.InlineKeyboardButton(text="⬆️", callback_data=f"{cb}_up_{right.id}"))
            else:
                sort_row.append(types.InlineKeyboardButton(text=" ", callback_data="noop"))

            # Правый элемент: вниз
            if i + 1 < total - 1:
                sort_row.append(types.InlineKeyboardButton(text="⬇️", callback_data=f"{cb}_down_{right.id}"))
            else:
                sort_row.append(types.InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*sort_row)


def _item_label(item) -> str:
    icon_map = {"text": "T", "photo": "img", "video": "vid", "document": "doc", "pptx": "pptx"}
    icon = icon_map.get(item.content_type, "")
    return f"[{icon}] {item.name}" if icon else item.name


def get_item_details_keyboard(item_id: int, category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"edit_item_name_{item_id}")
    builder.button(text="Описание", callback_data=f"edit_item_desc_{item_id}")
    builder.button(text="Заменить файл", callback_data=f"edit_item_file_{item_id}")
    builder.button(text="Удалить предмет", callback_data=f"del_item_{item_id}")
    builder.button(text="К категории", callback_data=f"nav_cat_{category_id}")
    builder.adjust(2)
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "admin_back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data=callback_data)
    return builder.as_markup()


def get_skip_keyboard(skip_callback: str = "admin_skip", back_callback: str = "admin_back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data=skip_callback)
    builder.button(text="Назад", callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()