"""
Модуль обеспечивает запросы к API.
Запрос осуществляется через сессию для безопасного закрытия.
Декоратор контролирует несколько запросов с логированием.
"""

import logging
import time
from functools import wraps

import requests

logger = logging.getLogger(__name__)


def retry(max_attempts, delay):
    """
    Декоратор, который оборачивает функцию логикой повторных попыток.

    :param max_attempts: Количество попыток до того, как будет выброшено исключение.
    :param delay: Время ожидания в секундах между попытками.
    :return: Результат выполнения оборачиваемой функции.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    return result
                except (
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                ) as e:
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Достигнуто максимальное количество попыток. Ошибка: {e}"
                        )
                        raise

                    logger.warning(
                        f"Ошибка сети (попытка {attempt + 1}/{max_attempts}). "
                        f"Ждем {delay} сек..."
                    )
                    time.sleep(delay)

        return wrapper

    return decorator


class ApiClient:
    """HTTP-клиент для выполнения GET-запросов к API."""

    def __init__(self, base_url: str, headers: dict | None = None):
        self.base_url = base_url
        self.headers = headers or {}
        if "Accept" not in self.headers:
            self.headers["Accept"] = "application/json"

    @retry(max_attempts=3, delay=2)
    def get_json(self, endpoint: str = "", params: dict | None = None):
        with requests.Session() as session:
            response = session.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=10,
            )
        response.raise_for_status()
        return response.json()
