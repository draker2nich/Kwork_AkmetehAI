import logging
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from sqlalchemy import text

from bot.database.ensure_db_created import create_database
from bot.utils.config import settings

engine = create_async_engine(settings.SQLALCHEMY_URL, echo=False,
                             pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=0)
async_session = async_sessionmaker(engine)

logger = logging.getLogger(__name__)


class Base(AsyncAttrs, DeclarativeBase):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id = mapped_column(BigInteger)
    full_name: Mapped[str] = mapped_column()
    username: Mapped[str] = mapped_column(nullable=True)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(nullable=True)

    parent_id: Mapped[int | None] = mapped_column(ForeignKey('categories.id'), nullable=True)

    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    parent: Mapped["Category | None"] = relationship("Category", back_populates="children", remote_side=[id])
    items: Mapped[list["Item"]] = relationship("Item", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)

    content_type: Mapped[str] = mapped_column(nullable=False, default="text")

    file_id: Mapped[str | None] = mapped_column(nullable=True)

    file_path: Mapped[str | None] = mapped_column(nullable=True)

    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    category: Mapped["Category"] = relationship("Category", back_populates="items")


async def on_startup_database():
    logger.info(f"Connecting to DB: {settings.SQLALCHEMY_DB_NAME} at {settings.SQLALCHEMY_IP}")
    create_database(settings.SQLALCHEMY_DB_NAME, settings.SQLALCHEMY_USER, settings.SQLALCHEMY_PASSWORD,
                    settings.SQLALCHEMY_IP, settings.SQLALCHEMY_PORT)

    logger.info(f"Registered tables: {Base.metadata.tables.keys()}")

    async with engine.begin() as conn:
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created (if not existed).")

        try:
            logger.info("Running migration for prompt_text...")
            async with conn.begin_nested():
                await conn.execute(text("ALTER TABLE categories ADD COLUMN prompt_text VARCHAR"))
            logger.info("Added prompt_text column to categories")
        except Exception as e:
            logger.info(f"Migration skipped (likely column exists): {e}")

    logger.info("Initializing categories...")
    from bot.database.initialization import create_initial_categories, sync_init_files
    await create_initial_categories()
    await sync_init_files()
