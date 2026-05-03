"""
Модуль отвечает за формирование списка монет.
Каждый парсер получает raw_data
(список словарей из JSON, в каждом словаре лежит информация по конкретной монете).
Парсер перебирает список словарей, извлекает из каждого нужные поля,
записывает их как атрибуты объекта Cryptocurrency и возвращает список готовых объектов.
"""

from abc import ABC, abstractmethod

from src.models import Cryptocurrency


class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров сырых данных API."""

    @abstractmethod
    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        """Принимает сырой список словарей, возвращает список объектов Cryptocurrency"""
        pass


class GeckoParser(BaseParser):
    """Парсер для данных CoinGecko API."""

    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        return [
            Cryptocurrency(
                name=item.get("name"),
                symbol=item.get("symbol"),
                price=item.get("current_price", 0),
                change_24h=item.get("price_change_percentage_24h", 0),
                volume=item.get("total_volume", 0),
                market_cap=item.get("market_cap", 0),
            )
            for item in raw_data
        ]


class CMCParser(BaseParser):
    """Парсер для данных CoinMarketCap API."""

    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        return [
            Cryptocurrency(
                name=item.get("name"),
                symbol=item.get("symbol"),
                price=usd.get("price", 0),
                change_24h=usd.get("percent_change_24h", 0),
                volume=usd.get("volume_24h", 0),
                market_cap=usd.get("market_cap", 0),
            )
            for item in raw_data
            if (usd := item.get("quote", {}).get("USD", {}))
        ]
