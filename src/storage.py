import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """Абстрактный базовый класс для сохранения результатов анализа в БД."""

    @abstractmethod
    def save(self, coins: list, results: dict) -> None:
        """Метод для сохранения результатов анализа в БД."""
        pass


class JsonStorage(BaseStorage):
    """Сохраняет результаты анализа в JSON-файл."""

    def __init__(self, filename: str = "crypto_report.json"):
        self.filename = filename

    def save(self, coins: list, results: dict) -> None:
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
    """Сохраняет результаты анализа в БД."""

    def __init__(self, db_path: str = "crypto_report.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

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

            conn.commit()

    def save(self, coins: list, results: dict) -> None:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

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

            conn.commit()
            logger.info("Данные сохранены в БД")
