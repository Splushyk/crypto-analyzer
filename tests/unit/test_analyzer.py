"""
Модуль unit-тестирования логики анализатора данных.

Проверяемые сценарии:
1. Корректность сортировки активов (top_up, top_down) и поиска максимального объема.
2. Расчет агрегированных метрик (total_market_cap).
3. Обработка краевых случаев: поведение системы при получении пустого списка данных.

Тесты являются чистыми unit-тестами, проверяющими бизнес-логику без использования моков.
"""

import pytest

from src.analyzer import CryptoAnalyzer
from src.models import Cryptocurrency


def test_analyze_data():
    coins = [
        Cryptocurrency("Coin1", "C1", 10.0, 1.0, 100.0, 10.0),
        Cryptocurrency("Coin2", "C2", 10.0, 2.0, 200.0, 20.0),
        Cryptocurrency("Coin3", "C3", 10.0, 3.0, 300.0, 30.0)
    ]
    analyzer = CryptoAnalyzer(coins)
    result = analyzer.analyze_data()

    assert [c.name for c in result["top_up"]] == ["Coin3", "Coin2", "Coin1"]
    assert [c.name for c in result["top_down"]] == ["Coin1", "Coin2", "Coin3"]
    assert result["max_volume"].name == "Coin3"
    assert result["total_market_cap"] == 60


def test_analyze_data_empty():
    """Проверяем, что анализатор не принимает пустые данные при создании"""
    with pytest.raises(ValueError, match="Данные для анализа не могут быть пустыми"):
        CryptoAnalyzer([])
