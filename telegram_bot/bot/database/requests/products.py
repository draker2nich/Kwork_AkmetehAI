import json
import logging

from sqlalchemy import select, update

from bot.database.models import async_session, Category, Item

logger = logging.getLogger(__name__)


async def export_categories_to_json(file_path: str = "categories.json"):
    """Экспортирует текущее дерево категорий в JSON файл."""
    async with async_session() as session:
        categories = await session.scalars(select(Category))
        all_categories = categories.all()

        items_result = await session.scalars(select(Item))
        all_items = items_result.all()

        items_map = {}
        for item in all_items:
            if item.category_id not in items_map:
                items_map[item.category_id] = []
            items_map[item.category_id].append(item)

        cat_map = {cat.id: cat for cat in all_categories}

        children_map = {}
        roots = []

        for cat in all_categories:
            if cat.parent_id is None:
                roots.append(cat)
            else:
                if cat.parent_id not in children_map:
                    children_map[cat.parent_id] = []
                children_map[cat.parent_id].append(cat)

        def build_tree(category_id):
            tree = {}
            children = children_map.get(category_id, [])

            for child in children:
                cat_items = items_map.get(child.id, [])
                items_data = []
                for item in cat_items:
                    items_data.append({
                        "name": item.name,
                        "description": item.description,
                        "content_type": item.content_type,
                        "file_id": item.file_id,
                        "file_path": item.file_path
                    })

                child_data = {
                    "prompt_text": child.prompt_text,
                    "items": items_data,
                    "subcategories": build_tree(child.id)
                }
                tree[child.name] = child_data
            return tree

        final_structure = {}
        for root in roots:
            cat_items = items_map.get(root.id, [])
            items_data = []
            for item in cat_items:
                items_data.append({
                    "name": item.name,
                    "description": item.description,
                    "content_type": item.content_type,
                    "file_id": item.file_id,
                    "file_path": item.file_path
                })

            final_structure[root.name] = {
                "prompt_text": root.prompt_text,
                "items": items_data,
                "subcategories": build_tree(root.id)
            }

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(final_structure, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error exporting categories to JSON: {e}")


async def get_root_categories():
    """Получить список корневых категорий (у которых нет родителя)"""
    async with async_session() as session:
        result = await session.scalars(select(Category).where(Category.parent_id.is_(None)))
        return result.all()


async def get_subcategories(category_id: int):
    """Получить подкатегории для заданной категории"""
    async with async_session() as session:
        result = await session.scalars(select(Category).where(Category.parent_id == category_id))
        return result.all()


async def get_category_by_id(category_id: int):
    """Получить категорию по ID"""
    async with async_session() as session:
        return await session.get(Category, category_id)


async def add_category(name: str, parent_id: int | None = None, prompt_text: str | None = None):
    """Создать новую категорию"""
    async with async_session() as session:
        category = Category(name=name, parent_id=parent_id, prompt_text=prompt_text)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        logger.info(f"Created category {category.id} ('{name}')")

    await export_categories_to_json()
    return category


async def update_category(category_id: int, **kwargs):
    """Обновить категорию"""
    async with async_session() as session:
        stmt = update(Category).where(Category.id == category_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Updated category {category_id} with {kwargs}")

    await export_categories_to_json()


async def delete_category(category_id: int):
    """Удалить категорию"""
    async with async_session() as session:
        category = await session.get(Category, category_id)
        if category:
            await session.delete(category)
            await session.commit()
            logger.info(f"Deleted category {category_id}")

    await export_categories_to_json()


async def get_category_full_path(category_id: int) -> list[str]:
    """
    Возвращает список имен категорий от корня до текущей.
    Например: ['Электроника', 'Телефоны', 'Apple']
    """
    async with async_session() as session:
        path = []
        current_id = category_id

        while current_id:
            category = await session.get(Category, current_id)
            if not category:
                break
            path.insert(0, category.name)
            current_id = category.parent_id

        return path


async def get_items_by_category(category_id: int):
    """Получить товары в категории"""
    async with async_session() as session:
        result = await session.scalars(select(Item).where(Item.category_id == category_id))
        return result.all()


async def get_item_by_id(item_id: int):
    """Получить товар по ID"""
    async with async_session() as session:
        return await session.get(Item, item_id)


async def add_item(name: str, category_id: int, content_type: str, description: str | None = None,
                   file_id: str | None = None, file_path: str | None = None):
    """Добавить новый товар"""
    async with async_session() as session:
        item = Item(
            name=name,
            category_id=category_id,
            content_type=content_type,
            description=description,
            file_id=file_id,
            file_path=file_path
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        logger.info(f"Added item {item.id} ('{name}') to category {category_id}")
        return item


async def update_item(item_id: int, **kwargs):
    """Обновить поля товара"""
    async with async_session() as session:
        stmt = update(Item).where(Item.id == item_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Updated item {item_id} with {kwargs}")


async def delete_item(item_id: int):
    """Удалить товар"""
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if item:
            await session.delete(item)
            await session.commit()
            logger.info(f"Deleted item {item_id}")
