import json
import logging
import os
import shutil

from sqlalchemy import select

from bot.database.models import Category, Item, async_session

logger = logging.getLogger(__name__)


async def create_initial_categories():
    async with async_session() as session:
        result = await session.execute(select(Category).limit(1))
        if result.scalar() is None:
            logger.info("Категорий не найдено... создаем из categories.json")

            try:
                with open("categories.json", "r", encoding="utf-8") as f:
                    initial_structure = json.load(f)
            except FileNotFoundError:
                logger.warning("Файл categories.json не найден!")
                initial_structure = {}
            except json.JSONDecodeError:
                logger.warning("Ошибка чтения JSON!")
                initial_structure = {}

            async def create_recursive(structure: dict, parent_id: int | None = None, path_stack: list[str] = []):
                cat_sort_order = 0
                for name, data in structure.items():
                    prompt_text = None
                    substructure = data
                    items_list = []
                    sort_order = cat_sort_order

                    if isinstance(data, dict) and ("prompt_text" in data or "subcategories" in data or "items" in data):
                        prompt_text = data.get("prompt_text")
                        substructure = data.get("subcategories", {})
                        items_list = data.get("items", [])
                        sort_order = data.get("sort_order", cat_sort_order)

                    category = Category(name=name, parent_id=parent_id, prompt_text=prompt_text, sort_order=sort_order)
                    session.add(category)
                    await session.flush()

                    current_path_stack = path_stack + [name]

                    item_sort_order = 0
                    for item_data in items_list:
                        file_path = item_data.get("file_path")
                        init_file = item_data.get("init_file")
                        item_sort = item_data.get("sort_order", item_sort_order)

                        if init_file and os.path.exists(init_file):
                            sanitized_stack = ["".join(c for c in n if c.isalnum() or c in (' ', '_', '-')).strip() for n in current_path_stack]
                            target_dir = os.path.join("files", *sanitized_stack)
                            os.makedirs(target_dir, exist_ok=True)

                            item_name = item_data.get("name", "item")
                            ext = os.path.splitext(init_file)[1]
                            safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '_', '-')).strip()
                            if not safe_name:
                                safe_name = "item"
                            target_filename = f"{safe_name}{ext}"
                            target_path = os.path.join(target_dir, target_filename)

                            try:
                                shutil.copy2(init_file, target_path)
                                file_path = target_path
                                logger.info(f"Copied init_file {init_file} to {file_path}")
                            except Exception as e:
                                logger.info(f"Error copying init_file {init_file}: {e}")

                        item = Item(
                            name=item_data.get("name"),
                            description=item_data.get("description"),
                            content_type=item_data.get("content_type", "text"),
                            file_id=item_data.get("file_id"),
                            file_path=file_path,
                            category_id=category.id,
                            sort_order=item_sort
                        )
                        session.add(item)
                        item_sort_order += 1

                    if substructure:
                        await create_recursive(substructure, category.id, current_path_stack)
                    
                    cat_sort_order += 1

            logger.info("Создание базовых категорий...")
            await create_recursive(initial_structure)
            await session.commit()
            logger.info("Базовые категории успешно созданы.")


async def sync_init_files():
    logger.info("Checking for missing init_files...")
    async with async_session() as session:
        try:
            with open("categories.json", "r", encoding="utf-8") as f:
                initial_structure = json.load(f)
        except Exception as e:
            logger.info(f"Error loading categories.json for sync: {e}")
            return

        async def sync_recursive(structure: dict, parent_id: int | None = None, path_stack: list[str] = []):
            for name, data in structure.items():
                stmt = select(Category).where(Category.name == name, Category.parent_id == parent_id)
                result = await session.execute(stmt)
                category = result.scalar()

                if not category:
                    continue

                items_list = []
                substructure = data
                if isinstance(data, dict) and ("prompt_text" in data or "subcategories" in data or "items" in data):
                    substructure = data.get("subcategories", {})
                    items_list = data.get("items", [])

                current_path_stack = path_stack + [name]

                for item_data in items_list:
                    item_name = item_data.get("name")
                    init_file = item_data.get("init_file")

                    if init_file:
                        stmt = select(Item).where(Item.name == item_name, Item.category_id == category.id)
                        result = await session.execute(stmt)
                        item = result.scalar()

                        if item:
                            need_copy = False
                            if not item.file_path:
                                need_copy = True
                            elif not os.path.exists(item.file_path):
                                need_copy = True

                            if need_copy:
                                if os.path.exists(init_file):
                                    sanitized_stack = ["".join(c for c in n if c.isalnum() or c in (' ', '_', '-')).strip() for n in current_path_stack]
                                    target_dir = os.path.join("files", *sanitized_stack)
                                    os.makedirs(target_dir, exist_ok=True)

                                    ext = os.path.splitext(init_file)[1]
                                    safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '_', '-')).strip()
                                    if not safe_name:
                                        safe_name = "item"
                                    target_filename = f"{safe_name}{ext}"
                                    target_path = os.path.join(target_dir, target_filename)

                                    try:
                                        shutil.copy2(init_file, target_path)
                                        item.file_path = target_path
                                        session.add(item)
                                        logger.info(f"Fixed file for item {item_name}: {target_path}")
                                    except Exception as e:
                                        logger.info(f"Error copying {init_file}: {e}")
                                else:
                                    logger.info(f"WARNING: init_file not found: {init_file}")

                if substructure:
                    await sync_recursive(substructure, category.id, current_path_stack)

        await sync_recursive(initial_structure)
        await session.commit()