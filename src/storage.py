import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """Абстрактный базовый класс для сохранения результатов анализа в БД."""

    @abstractmethod
    def save(self, results: dict) -> None:
        """Метод для сохранения результатов анализа в БД."""
        pass


class JsonStorage(BaseStorage):
    """Сохраняет результаты анализа в JSON-файл."""

    def __init__(self, filename: str = "crypto_report.json"):
        self.filename = filename

    def save(self, results: dict) -> None:
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
