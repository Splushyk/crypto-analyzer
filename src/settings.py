"""
Модуль читает переменные окружения через python-dotenv
и предоставляет типизированный конфиг.
"""

import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)


class StorageType(Enum):
    """Допустимые типы хранилища."""

    JSON = "json"
    SQLITE = "sqlite"


class Settings:
    """Конфигурация приложения на основе переменных окружения."""

    storage: StorageType = StorageType(os.getenv("STORAGE", "json"))


settings = Settings()
