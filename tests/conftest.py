import pytest

from src.models import Cryptocurrency
from src.storage import SqliteStorage


@pytest.fixture
def sample_coin():
    """
    Возвращает эталонный объект криптовалюты для тестов.
    Данные содержат дробные части для проверки точности сохранения в БД.
    """
    return Cryptocurrency(
        name="SomeCoin",
        symbol="SC",
        price=10.12345,
        change_24h=8.12345,
        volume=555.12345,
        market_cap=777.12345
    )


@pytest.fixture
def sample_results(sample_coin):
    """Возвращает эталонный словарь с результатами анализа криптовалют."""
    return {
        "top_up": [sample_coin],
        "top_down": [sample_coin],
        "max_volume": sample_coin,
        "total_market_cap": 777.12345
    }


@pytest.fixture
def sqlite_storage():
    """Создает изолированное хранилище в памяти для каждого теста."""
    with SqliteStorage(":memory:") as storage:
        yield storage
