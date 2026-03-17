"""
Модуль осуществляет анализ списка криптовалют. Получает список объектов Cryptocurrency,
сортирует по нужным ключам и возвращает словарь, где ключ - это критерий сортировки,
а значение - список отобранных монет.
"""

from src.models import Cryptocurrency


class CryptoAnalyzer:
    """Анализирует список криптовалют: топ роста, падения, объёма и капитализации."""

    def __init__(self, data: list[Cryptocurrency]):
        self.data = data

    def get_top_coins(self, attr: str, n: int = 3, reverse: bool = True):
        """Внутренний метод для сортировки объектов по любому атрибуту"""
        return sorted(
            self.data,
            key=lambda x: getattr(x, attr) or 0,
            reverse=reverse
        )[:n]

    def analyze_data(self, top: int = 3):
        """Основной метод, который возвращает словарь со всеми расчетами"""
        top_up = self.get_top_coins("change_24h", n=top)
        top_down = self.get_top_coins("change_24h", n=top, reverse=False)
        max_volume = self.get_top_coins("volume", n=1)[0]
        total_market_cap = sum(coin.market_cap for coin in self.data)

        return {
            "top_up": top_up,
            "top_down": top_down,
            "max_volume": max_volume,
            "total_market_cap": total_market_cap
        }
