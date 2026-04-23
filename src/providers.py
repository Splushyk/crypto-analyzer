"""
Модуль является связующим звеном между API и парсером.
Провайдер сам не делает запросы и сам не парсит, а организует поток.
Каждый провайдер знает свою специфику.
"""

import logging
from abc import ABC, abstractmethod

from src.api_client import ApiClient
from src.models import Cryptocurrency
from src.parsers import BaseParser

logger = logging.getLogger(__name__)


class CryptoProvider(ABC):
    """Абстрактный базовый класс для провайдеров криптовалютных данных."""

    @abstractmethod
    def get_coins(self) -> list[Cryptocurrency]:
        """Должен вернуть список объектов Cryptocurrency"""
        pass


class GeckoProvider(CryptoProvider):
    """Провайдер данных CoinGecko. Получает топ-50 монет по капитализации."""

    def __init__(self, client: ApiClient, parser: BaseParser):
        self.params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
        }
        self.client = client
        self.parser = parser

    def get_coins(self) -> list[Cryptocurrency]:
        raw_data = self.client.get_json(params=self.params)
        coins = self.parser.parse(raw_data)
        logger.info(f"Получено {len(coins)} монет от CoinGecko")
        return coins


class CMCProvider(CryptoProvider):
    """
    Провайдер данных CoinMarketCap.
    Требует API-ключ в переменной окружения CMC_API_KEY.
    """

    def __init__(self, client: ApiClient, parser: BaseParser):
        self.client = client
        self.parser = parser

    def get_coins(self) -> list[Cryptocurrency]:
        params = {"start": "1", "limit": "50", "convert": "USD"}
        raw_response = self.client.get_json(params=params)
        coins_list = raw_response.get("data", [])
        logger.info(f"Получено {len(coins_list)} монет от CoinMarketCap")
        return self.parser.parse(coins_list)
