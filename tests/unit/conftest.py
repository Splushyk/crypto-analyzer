import pytest

from src.api_client import ApiClient
from src.models import Cryptocurrency


@pytest.fixture
def gecko_raw_data():
    return [
        {
            "name": "SomeCoin",
            "symbol": "SC",
            "current_price": 10.12345,
            "price_change_percentage_24h": 8.12345,
            "total_volume": 555.12345,
            "market_cap": 777.12345,
        }
    ]


@pytest.fixture
def cmc_raw_data():
    return [
        {
            "name": "SomeCoin",
            "symbol": "SC",
            "quote": {
                "USD": {
                    "price": 10.12345,
                    "percent_change_24h": 8.12345,
                    "volume_24h": 555.12345,
                    "market_cap": 777.12345,
                }
            }
        }
    ]


@pytest.fixture
def api_client():
    client = ApiClient(base_url="https://fake-api.com")
    return client


@pytest.fixture
def mock_response(mocker):
    """Создает только объект ответа."""
    mock_res = mocker.Mock()
    mock_res.raise_for_status.return_value = None
    mock_res.json.return_value = {"some_item": "some_value"}
    return mock_res


@pytest.fixture
def mock_session(mocker, mock_response):
    """Создает сессию, патчит ее и связывает с mock_response."""
    mock_sess = mocker.Mock()
    # Настройка контекстного менеджера (with requests.Session() as session)
    mock_sess.__enter__ = mocker.Mock(return_value=mock_sess)
    mock_sess.__exit__ = mocker.Mock(return_value=False)

    # Настраиваем методы сессии
    mock_sess.request.return_value = mock_response
    mock_sess.get.return_value = mock_response
    mock_sess.post.return_value = mock_response

    # Патчим импорт в целевом модуле
    mocker.patch("src.api_client.requests.Session", return_value=mock_sess)

    return mock_sess
