import pytest
from django.contrib.auth.models import User

from src.models import Cryptocurrency
from src.storage import SqliteStorage


def pytest_collection_modifyitems(items):
    for item in items:
        path = str(item.fspath)
        if "/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in path:
            item.add_marker(pytest.mark.integration)


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
        market_cap=777.12345,
    )


@pytest.fixture
def sample_results(sample_coin):
    """Возвращает эталонный словарь с результатами анализа криптовалют."""
    return {
        "top_up": [sample_coin],
        "top_down": [sample_coin],
        "max_volume": sample_coin,
        "total_market_cap": 777.12345,
    }


@pytest.fixture
def sqlite_storage():
    """Создает изолированное хранилище в памяти для каждого теста."""
    with SqliteStorage(":memory:") as storage:
        yield storage


@pytest.fixture
def user_a(db):
    """Тестовый пользователь A."""
    return User.objects.create_user(username="name_a", password="password123")


@pytest.fixture
def user_b(db):
    """Тестовый пользователь B."""
    return User.objects.create_user(username="name_b", password="password456")


@pytest.fixture
def admin_user(db):
    """Тестовый пользователь со staff-правами."""
    return User.objects.create_user(
        username="admin_test", password="adminpass123", is_staff=True
    )


@pytest.fixture
def mock_api_symbol_found(mocker):
    """
    Мокает ApiClient так, чтобы API нашёл монету BTC.
    mocker.patch подменяет класс ApiClient внутри модуля crypto.services —
    чтобы при вызове validate_symbol не было реального HTTP-запроса.
    """
    fake_response = {
        "coins": [
            {"symbol": "BTC", "name": "Bitcoin", "id": "bitcoin"},
        ]
    }
    mock_client = mocker.patch("crypto.services.ApiClient")
    mock_client.return_value.get_json.return_value = fake_response
    return mock_client


@pytest.fixture
def mock_api_symbol_not_found(mocker):
    """Мокает ApiClient так, чтобы API вернул пустой список."""
    fake_response: dict[str, list] = {"coins": []}
    mock_client = mocker.patch("crypto.services.ApiClient")
    mock_client.return_value.get_json.return_value = fake_response
    return mock_client
