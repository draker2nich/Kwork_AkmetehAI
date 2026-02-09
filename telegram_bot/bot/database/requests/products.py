import json
import logging

from sqlalchemy import select, update, func

from bot.database.models import async_session, Category, Item

logger = logging.getLogger(__name__)


async def export_categories_to_json(file_path: str = "categories.json"):
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
            children.sort(key=lambda x: x.sort_order)
            for child in children:
                cat_items = items_map.get(child.id, [])
                cat_items.sort(key=lambda x: x.sort_order)
                items_data = []
                for item in cat_items:
                    items_data.append({
                        "name": item.name, "description": item.description,
                        "content_type": item.content_type, "file_id": item.file_id,
                        "file_path": item.file_path, "sort_order": item.sort_order
                    })
                child_data = {
                    "prompt_text": child.prompt_text, "sort_order": child.sort_order,
                    "items": items_data, "subcategories": build_tree(child.id)
                }
                tree[child.name] = child_data
            return tree

        final_structure = {}
        roots.sort(key=lambda x: x.sort_order)
        for root in roots:
            cat_items = items_map.get(root.id, [])
            cat_items.sort(key=lambda x: x.sort_order)
            items_data = []
            for item in cat_items:
                items_data.append({
                    "name": item.name, "description": item.description,
                    "content_type": item.content_type, "file_id": item.file_id,
                    "file_path": item.file_path, "sort_order": item.sort_order
                })
            final_structure[root.name] = {
                "prompt_text": root.prompt_text, "sort_order": root.sort_order,
                "items": items_data, "subcategories": build_tree(root.id)
            }

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(final_structure, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error exporting categories to JSON: {e}")


async def get_root_categories():
    async with async_session() as session:
        result = await session.scalars(
            select(Category).where(Category.parent_id.is_(None))
            .order_by(Category.sort_order, Category.id)
        )
        return result.all()


async def get_subcategories(category_id: int):
    async with async_session() as session:
        result = await session.scalars(
            select(Category).where(Category.parent_id == category_id)
            .order_by(Category.sort_order, Category.id)
        )
        return result.all()


async def get_category_by_id(category_id: int):
    async with async_session() as session:
        return await session.get(Category, category_id)


async def get_next_category_sort_order(parent_id: int | None) -> int:
    async with async_session() as session:
        result = await session.scalar(
            select(func.coalesce(func.max(Category.sort_order), -1) + 1)
            .where(Category.parent_id == parent_id if parent_id else Category.parent_id.is_(None))
        )
        return result or 0


async def add_category(name: str, parent_id: int | None = None, prompt_text: str | None = None):
    async with async_session() as session:
        sort_order = await get_next_category_sort_order(parent_id)
        category = Category(name=name, parent_id=parent_id, prompt_text=prompt_text, sort_order=sort_order)
        session.add(category)
        await session.commit()
        await session.refresh(category)
    await export_categories_to_json()
    return category


async def update_category(category_id: int, **kwargs):
    async with async_session() as session:
        stmt = update(Category).where(Category.id == category_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()
    await export_categories_to_json()


async def delete_category(category_id: int):
    async with async_session() as session:
        category = await session.get(Category, category_id)
        if category:
            await session.delete(category)
            await session.commit()
    await export_categories_to_json()


async def move_category(category_id: int, direction: str) -> bool:
    async with async_session() as session:
        category = await session.get(Category, category_id)
        if not category:
            return False
        if category.parent_id is None:
            siblings = await session.scalars(
                select(Category).where(Category.parent_id.is_(None))
                .order_by(Category.sort_order, Category.id)
            )
        else:
            siblings = await session.scalars(
                select(Category).where(Category.parent_id == category.parent_id)
                .order_by(Category.sort_order, Category.id)
            )
        siblings_list = list(siblings.all())
        current_idx = next((i for i, c in enumerate(siblings_list) if c.id == category_id), None)
        if current_idx is None:
            return False
        if direction == "up" and current_idx > 0:
            swap_idx = current_idx - 1
        elif direction == "down" and current_idx < len(siblings_list) - 1:
            swap_idx = current_idx + 1
        else:
            return False
        cat1, cat2 = siblings_list[current_idx], siblings_list[swap_idx]
        cat1.sort_order, cat2.sort_order = cat2.sort_order, cat1.sort_order
        if cat1.sort_order == cat2.sort_order:
            cat1.sort_order = current_idx
            cat2.sort_order = swap_idx
            if direction == "up":
                cat1.sort_order, cat2.sort_order = cat2.sort_order, cat1.sort_order
        session.add(cat1)
        session.add(cat2)
        await session.commit()
    await export_categories_to_json()
    return True


async def swap_elements(id_a: int, id_b: int, is_category: bool) -> bool:
    """Поменять местами sort_order двух элементов (категорий или предметов)."""
    Model = Category if is_category else Item
    async with async_session() as session:
        a = await session.get(Model, id_a)
        b = await session.get(Model, id_b)
        if not a or not b:
            return False
        a.sort_order, b.sort_order = b.sort_order, a.sort_order
        if a.sort_order == b.sort_order:
            a.sort_order, b.sort_order = 0, 1
        session.add(a)
        session.add(b)
        await session.commit()
    if is_category:
        await export_categories_to_json()
    return True


async def get_category_full_path(category_id: int) -> list[str]:
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
    async with async_session() as session:
        result = await session.scalars(
            select(Item).where(Item.category_id == category_id)
            .order_by(Item.sort_order, Item.id)
        )
        return result.all()


async def get_item_by_id(item_id: int):
    async with async_session() as session:
        return await session.get(Item, item_id)


async def get_next_item_sort_order(category_id: int) -> int:
    async with async_session() as session:
        result = await session.scalar(
            select(func.coalesce(func.max(Item.sort_order), -1) + 1)
            .where(Item.category_id == category_id)
        )
        return result or 0


async def add_item(name: str, category_id: int, content_type: str, description: str | None = None,
                   file_id: str | None = None, file_path: str | None = None):
    async with async_session() as session:
        sort_order = await get_next_item_sort_order(category_id)
        item = Item(
            name=name, category_id=category_id, content_type=content_type,
            description=description, file_id=file_id, file_path=file_path,
            sort_order=sort_order
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


async def update_item(item_id: int, **kwargs):
    async with async_session() as session:
        stmt = update(Item).where(Item.id == item_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()


async def delete_item(item_id: int):
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if item:
            await session.delete(item)
            await session.commit()


async def move_item(item_id: int, direction: str) -> bool:
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if not item:
            return False
        siblings = await session.scalars(
            select(Item).where(Item.category_id == item.category_id)
            .order_by(Item.sort_order, Item.id)
        )
        siblings_list = list(siblings.all())
        current_idx = next((i for i, it in enumerate(siblings_list) if it.id == item_id), None)
        if current_idx is None:
            return False
        if direction == "up" and current_idx > 0:
            swap_idx = current_idx - 1
        elif direction == "down" and current_idx < len(siblings_list) - 1:
            swap_idx = current_idx + 1
        else:
            return False
        item1, item2 = siblings_list[current_idx], siblings_list[swap_idx]
        item1.sort_order, item2.sort_order = item2.sort_order, item1.sort_order
        if item1.sort_order == item2.sort_order:
            item1.sort_order = current_idx
            item2.sort_order = swap_idx
            if direction == "up":
                item1.sort_order, item2.sort_order = item2.sort_order, item1.sort_order
        session.add(item1)
        session.add(item2)
        await session.commit()
    return True