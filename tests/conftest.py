import pytest


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
