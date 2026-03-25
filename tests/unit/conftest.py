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
def mock_session(mocker):
    mock_response = mocker.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"some_item": "some_value"}

    mock_session = mocker.Mock()
    mock_session.__enter__ = mocker.Mock(return_value=mock_session)
    mock_session.__exit__ = mocker.Mock(return_value=False)

    mocker.patch("src.api_client.requests.Session", return_value=mock_session)
    return mock_session, mock_response
