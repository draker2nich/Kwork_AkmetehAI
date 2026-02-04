import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

if not os.getenv("TG_TOKEN"):
    from dotenv import load_dotenv

    load_dotenv("../.env")


class Settings(BaseSettings):
    """
    Основные настройки проекта.

    Значения берутся из переменных окружения и/или файла `.env`
    (в рабочей директории процесса).
    """

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    TG_TOKEN: str

    SQLALCHEMY_DB_NAME: str
    SQLALCHEMY_IP: str
    SQLALCHEMY_PORT: int
    SQLALCHEMY_USER: str
    SQLALCHEMY_PASSWORD: str

    ADMIN_IDS_RAW: Optional[str] = None

    REDIS_URL: Optional[str] = None

    @property
    def SQLALCHEMY_URL(self) -> str:
        """
        Собираем URL подключения к БД из компонент.
        """
        return (
            f"postgresql+asyncpg://"
            f"{self.SQLALCHEMY_USER}:{self.SQLALCHEMY_PASSWORD}"
            f"@{self.SQLALCHEMY_IP}:{self.SQLALCHEMY_PORT}/{self.SQLALCHEMY_DB_NAME}"
        )

    @property
    def ADMIN_IDS(self) -> List[int]:
        """
        Возвращает список ID администраторов в виде List[int].

        Поддерживает форматы:
        - "1 2 3"
        - "1,2,3"
        - одиночное число "1"
        """
        raw = self.ADMIN_IDS_RAW
        if not raw:
            return []
        parts = raw.replace(",", " ").split()
        return [int(x) for x in parts]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Кешируем инстанс настроек, чтобы не перечитывать .env много раз.
    """
    return Settings()


settings = get_settings()
