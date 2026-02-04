from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, delete, func, case
from sqlalchemy.exc import SQLAlchemyError

from bot.database.models import async_session, User


async def get_users():
    async with async_session() as session:
        result = await session.scalars(select(User))
        return [r for r in result]


async def get_user_ids():
    async with async_session() as session:
        result = await session.scalars(select(User.user_id))
        return result.all()


async def add_user(user_id: int, **kwargs) -> User:
    async with async_session() as session:
        try:
            user = await session.scalar(select(User).where(User.user_id == user_id))

            if not user:
                user = User(user_id=user_id, **kwargs)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            return user

        except SQLAlchemyError:
            await session.rollback()
            raise


async def get_user(user_id: int) -> User:
    async with async_session() as session:
        result = await session.scalar(select(User).where(User.user_id == user_id))
        return result


async def update_user(user_id: int, **kwargs):
    async with async_session() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(**kwargs))
        await session.commit()


async def delete_user(user_id: int):
    async with async_session() as session:
        await session.execute(delete(User).where(User.user_id == user_id))
        await session.commit()


async def get_user_stats() -> dict:
    """
    Возвращает агрегированную статистику пользователей.

    Ключи в словаре:
        - total_users
        - new_users_24h, new_users_3d, new_users_7d, new_users_30d
        - active_users_24h, active_users_3d, active_users_7d, active_users_30d
    """
    now = datetime.now(timezone.utc)

    thresholds = {
        "24h": now - timedelta(hours=24),
        "3d": now - timedelta(days=3),
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
    }

    async with async_session() as session:
        result = await session.execute(
            select(
                func.count(User.id).label("total_users"),

                func.count(
                    case((User.created_at >= thresholds["24h"], 1))
                ).label("new_users_24h"),
                func.count(
                    case((User.created_at >= thresholds["3d"], 1))
                ).label("new_users_3d"),
                func.count(
                    case((User.created_at >= thresholds["7d"], 1))
                ).label("new_users_7d"),
                func.count(
                    case((User.created_at >= thresholds["30d"], 1))
                ).label("new_users_30d"),

                func.count(
                    case((User.last_activity >= thresholds["24h"], 1))
                ).label("active_users_24h"),
                func.count(
                    case((User.last_activity >= thresholds["3d"], 1))
                ).label("active_users_3d"),
                func.count(
                    case((User.last_activity >= thresholds["7d"], 1))
                ).label("active_users_7d"),
                func.count(
                    case((User.last_activity >= thresholds["30d"], 1))
                ).label("active_users_30d"),
            )
        )

        row = result.one()

        return {
            "total_users": row.total_users,
            "new_users_24h": row.new_users_24h,
            "new_users_3d": row.new_users_3d,
            "new_users_7d": row.new_users_7d,
            "new_users_30d": row.new_users_30d,
            "active_users_24h": row.active_users_24h,
            "active_users_3d": row.active_users_3d,
            "active_users_7d": row.active_users_7d,
            "active_users_30d": row.active_users_30d,
        }
