"""
Модуль для управления долгосрочным хранением данных анализа криптовалют.

Реализует слой абстракции Хранилища (Data Access Layer), позволяя прозрачно
переключаться между различными форматами хранения (JSON, SQLite) через
единый интерфейс BaseStorage.

Основные компоненты:
    - BaseStorage: Абстрактный базовый класс, определяющий контракт для всех хранилищ.
    - JsonStorage: Реализация для сохранения итоговых отчетов в формате JSON.
    - SqliteStorage: Реляционное хранилище с поддержкой истории снимков (snapshots)
      и аналитическими SQL-запросами (сравнение периодов, история цен).

Принцип работы основан на паттерне 'Стратегия', что позволяет main.py не зависеть
от конкретной реализации базы данных.
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """
    Интерфейс хранилища данных.

    Обязательно реализует сохранение (save).
    Методы аналитики являются опциональными.
    """

    @abstractmethod
    def save(self, coins: list, results: dict) -> None:
        """Сохраняет данные текущего анализа в долгосрочное хранилище."""
        pass

    def get_all_snapshots(self) -> list[dict]:
        """(Опционально) Возвращает список всех сохраненных снимков."""
        raise NotImplementedError("Это хранилище не поддерживает просмотр списка снимков.")

    def get_snapshot_comparison(self, snapshot_id_1: int, snapshot_id_2: int):
        """(Опционально) Возвращает разницу цен между двумя снимками."""
        raise NotImplementedError("Это хранилище не поддерживает аналитику.")

    def get_coin_history(self, symbol: str) -> list[dict]:
        """(Опционально) Возвращает историю изменения цены конкретной монеты."""
        raise NotImplementedError("Это хранилище не поддерживает аналитику.")

    def get_top_movers(self) -> dict[str, list[dict]]:
        """(Опционально) Возвращает лидеров роста и падения за последний снимок."""
        raise NotImplementedError("Это хранилище не поддерживает аналитику.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class JsonStorage(BaseStorage):
    """Хранилище для записи результатов анализа в статичный JSON-файл."""

    def __init__(self, filename: str = "crypto_report.json"):
        self.filename = filename

    def save(self, coins: list, results: dict) -> None:
        """Формирует отчет и сохраняет его в JSON."""
        date = datetime.now()
        report = {
            "generated_at": date.strftime("%Y-%m-%d %H-%M-%S"),
            "total_market_cap_usd": results["total_market_cap"],
            "top_gainers": [
                {"name": c.name, "symbol": c.symbol, "change_24h": c.change_24h}
                for c in results["top_up"]
            ],
            "top_losers": [
                {"name": c.name, "symbol": c.symbol, "change_24h": c.change_24h}
                for c in results["top_down"]
            ],
            "highest_volume": {
                "name": results["max_volume"].name,
                "symbol": results["max_volume"].symbol,
                "volume": results["max_volume"].volume
            }
        }

        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4, ensure_ascii=False)

        logger.info(f"Отчет успешно сохранен в JSON-файл: {self.filename}")


class SqliteStorage(BaseStorage):
    """Реляционное хранилище с поддержкой SQL-аналитики."""

    def __init__(self, db_path: str = "crypto_report.db"):
        self.db_path = db_path
        # Открываем соединение сразу
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Гарантируем закрытие при выходе из with
        self.conn.close()

    def _init_db(self) -> None:
        """Создает таблицы snapshots и coin_prices, если они отсутствуют."""
        with self.conn:
            cursor = self.conn.cursor()

            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS snapshots
                           (
                               id               INTEGER PRIMARY KEY AUTOINCREMENT,
                               created_at       TIMESTAMP NOT NULL,
                               total_market_cap REAL      NOT NULL
                           )
                           """)

            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS coin_prices
                           (
                               id          INTEGER PRIMARY KEY AUTOINCREMENT,
                               snapshot_id INTEGER NOT NULL,
                               name        TEXT    NOT NULL,
                               symbol      TEXT    NOT NULL,
                               price       REAL    NOT NULL,
                               change_24h  REAL    NOT NULL,
                               volume      REAL    NOT NULL,
                               market_cap  REAL    NOT NULL,
                               FOREIGN KEY (snapshot_id) REFERENCES snapshots (id) ON DELETE CASCADE
                           )
                           """)

    def save(self, coins: list, results: dict) -> None:
        """Записывает новый снимок и все связанные цены монет в БД."""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.conn:
            cursor = self.conn.cursor()

            cursor.execute(
                "INSERT INTO snapshots (created_at, total_market_cap) VALUES (?, ?)",
                (created_at, results["total_market_cap"])
            )
            snapshot_id = cursor.lastrowid

            cursor.executemany(
                "INSERT INTO coin_prices (snapshot_id, name, symbol, price, change_24h, volume, market_cap) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (snapshot_id, coin.name, coin.symbol, coin.price, coin.change_24h, coin.volume, coin.market_cap)
                    for coin in coins
                ]
            )

            logger.info("Данные успешно сохранены в SQLite")

    def get_all_snapshots(self) -> list[dict]:
        """Возвращает список всех снимков (ID, дата, общая капитализация)."""
        query = "SELECT id, created_at, total_market_cap FROM snapshots ORDER BY id ASC"
        # Используем self.conn напрямую
        cursor = self.conn.cursor()
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_snapshot_compare(self, snapshot_id_1: int, snapshot_id_2: int) -> list[dict]:
        """Сравнивает цены монет между двумя снимками."""
        query = """
                SELECT t1.symbol,
                       t1.price                                            AS old_price,
                       t2.price                                            AS new_price,
                       (t2.price - t1.price)                               AS price_diff,
                       ((t2.price - t1.price) / NULLIF(t1.price, 0) * 100) AS percent_change
                FROM coin_prices AS t1
                         JOIN coin_prices AS t2
                              ON t1.symbol = t2.symbol
                WHERE t1.snapshot_id = ?
                  AND t2.snapshot_id = ?
                ORDER BY percent_change DESC
                """
        # Используем self.conn напрямую
        cursor = self.conn.cursor()
        cursor.execute(query, (snapshot_id_1, snapshot_id_2))
        return [dict(row) for row in cursor.fetchall()]

    def get_coin_history(self, symbol: str) -> list[dict]:
        """Получает историю цен конкретной монеты."""
        query = """
                SELECT s.created_at, cp.price
                FROM coin_prices AS cp
                         JOIN snapshots AS s
                              ON cp.snapshot_id = s.id
                WHERE cp.symbol = ?
                ORDER BY s.created_at ASC
                """
        # Используем self.conn напрямую
        cursor = self.conn.cursor()
        cursor.execute(query, (symbol.upper(),))
        return [dict(row) for row in cursor.fetchall()]

    def get_top_movers(self) -> dict[str, list[dict]]:
        """
        Возвращает фиксированный топ-5 монет по росту и топ-5 по падению
        за последний снимок.
        """
        # Запрос для лидеров роста
        query_up = """
                   SELECT symbol, price, change_24h
                   FROM coin_prices
                   WHERE snapshot_id = (SELECT MAX(id) FROM snapshots)
                   ORDER BY change_24h DESC
                   LIMIT 5
                   """
        # Запрос для лидеров падения
        query_down = """
                     SELECT symbol, price, change_24h
                     FROM coin_prices
                     WHERE snapshot_id = (SELECT MAX(id) FROM snapshots)
                     ORDER BY change_24h ASC
                     LIMIT 5
                     """

        # Используем self.conn напрямую
        cursor = self.conn.cursor()

        cursor.execute(query_up)
        gainers = [dict(row) for row in cursor.fetchall()]

        cursor.execute(query_down)
        losers = [dict(row) for row in cursor.fetchall()]

        return {
            "gainers": gainers,
            "losers": losers
        }
