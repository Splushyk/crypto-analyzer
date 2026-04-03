"""
Тесты для модели криптовалюты (валидация данных и строковое представление).
"""

import pytest

from src.models import Cryptocurrency



def test_cryptocurrency_model_creation(sample_coin):
    assert sample_coin.name == "SomeCoin"
    assert sample_coin.symbol == "SC"
    assert sample_coin.price == 10.12345
    assert sample_coin.change_24h == 8.12345
    assert sample_coin.volume == 555.12345
    assert sample_coin.market_cap == 777.12345


@pytest.mark.parametrize("overrides, attr, expected", [
    ({"symbol": "sc"}, "symbol", "SC"),  # Тестируем приведение к верхнему регистру
    ({"price": None}, "price", 0.0),  # Тестируем защиту от None
    ({"change_24h": None}, "change_24h", 0.0),
    ({"volume": None}, "volume", 0.0),
    ({"market_cap": None}, "market_cap", 0.0),
], ids=[
    "symbol_uppercase",
    "price_none",
    "change_24h_none",
    "volume_none",
    "market_cap_none"
])
def test_cryptocurrency_fields(overrides, attr, expected):
    full_data = {
        "name": "SomeCoin",
        "symbol": "SC",
        "price": 1.0,
        "change_24h": 1.0,
        "volume": 1.0,
        "market_cap": 1.0
    }
    full_data.update(overrides)

    coin = Cryptocurrency(**full_data)
    assert getattr(coin, attr) == expected


@pytest.mark.parametrize("args, expected", [
    (["SomeCoin", "sc", 1.12345, 1.12345, 1.0, 1.0], "SomeCoin (SC): $1.12 (+1.12%)"),
    (["SomeCoin", "sc", 1.12345, -1.12345, 1.0, 1.0], "SomeCoin (SC): $1.12 (-1.12%)")
], ids=["positive_change", "negative_change"])
def test_str(args, expected):
    coin = Cryptocurrency(*args)
    assert str(coin) == expected


@pytest.mark.parametrize("version1, version2, expected", [
    (1.0, 5.0, True),
    (5.0, 1.0, False),
    (1.0, 1.0, False)
], ids=["less", "greater", "equal"])
def test_lt(version1, version2, expected):
    coin1 = Cryptocurrency("A", "A", 1.0, version1, 1.0, 1.0)
    coin2 = Cryptocurrency("B", "B", 1.0, version2, 1.0, 1.0)
    assert (coin1 < coin2) == expected


def test_lt_not_implemented():
    coin = Cryptocurrency("A", "A", 1.0, 1.0, 1.0, 1.0)
    assert coin.__lt__("not a coin") == NotImplemented
