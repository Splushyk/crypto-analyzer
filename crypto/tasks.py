import os

from celery import shared_task
from requests.exceptions import RequestException

from crypto.models import CoinPrice, Snapshot
from src.analyzer import CryptoAnalyzer
from src.api_client import ApiClient
from src.parsers import CMCParser, GeckoParser
from src.providers import CMCProvider, GeckoProvider

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"


def _build_provider(source):
    """Создаёт и возвращает провайдер данных по имени источника."""
    if source == "coingecko":
        return GeckoProvider(
            client=ApiClient(base_url=COINGECKO_URL), parser=GeckoParser()
        )
    if source == "cmc":
        api_key = os.getenv("CMC_API_KEY")
        if not api_key:
            raise ValueError("Не найден CMC_API_KEY в переменных окружения!")
        return CMCProvider(
            client=ApiClient(base_url=CMC_URL, headers={"X-CMC_PRO_API_KEY": api_key}),
            parser=CMCParser(),
        )
    raise ValueError(f"Неизвестный источник: {source}")


def _save_snapshot(coins, total_cap):
    """Сохраняет снимок рынка и цены монет в БД. Возвращает id снимка."""
    snapshot = Snapshot.objects.create(total_market_cap=total_cap)
    CoinPrice.objects.bulk_create(
        [
            CoinPrice(
                snapshot=snapshot,
                name=c.name,
                symbol=c.symbol,
                price=c.price,
                change_24h=c.change_24h,
                volume=c.volume,
                market_cap=c.market_cap,
            )
            for c in coins
        ]
    )
    return snapshot.id


@shared_task(
    autoretry_for=(RequestException,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def fetch_snapshot_task(source="coingecko"):
    """Celery-задача: получает данные от API и сохраняет снимок в БД."""
    provider = _build_provider(source)
    coins = provider.get_coins()
    total_cap = CryptoAnalyzer(coins).analyze_data()["total_market_cap"]
    snapshot_id = _save_snapshot(coins, total_cap)
    return snapshot_id
