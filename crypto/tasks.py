import os

from celery import shared_task
from django.core.cache import cache
from requests.exceptions import RequestException

from crypto.cache import (
    ANALYTICS_CACHE_TTL,
    CACHE_KEY_MARKET_STATS,
    CACHE_KEY_TOP_MOVERS,
    CACHE_KEY_VOLUME_LEADERS,
    invalidate_coin_history,
)
from crypto.models import CoinPrice, Snapshot
from crypto.serializers import (
    MarketStatsSerializer,
    TopMoversSerializer,
    VolumeLeadersSerializer,
)
from crypto.services import get_market_stats, get_top_movers, get_volume_leaders
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


def _cache_analytics() -> None:
    """Пересчитывает аналитику по последнему снимку и кладёт в кеш."""
    stats = get_market_stats()
    if stats is not None:
        cache.set(
            CACHE_KEY_MARKET_STATS,
            MarketStatsSerializer(stats).data,
            ANALYTICS_CACHE_TTL,
        )

    movers = get_top_movers()
    if movers is not None:
        cache.set(
            CACHE_KEY_TOP_MOVERS,
            TopMoversSerializer(movers).data,
            ANALYTICS_CACHE_TTL,
        )

    leaders = get_volume_leaders()
    if leaders is not None:
        cache.set(
            CACHE_KEY_VOLUME_LEADERS,
            VolumeLeadersSerializer(leaders).data,
            ANALYTICS_CACHE_TTL,
        )


@shared_task(
    autoretry_for=(RequestException,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=60,
    time_limit=120,
)
def fetch_snapshot_task(source="coingecko"):
    """Celery-задача: получает данные от API и сохраняет снимок в БД."""
    provider = _build_provider(source)
    coins = provider.get_coins()
    total_cap = CryptoAnalyzer(coins).analyze_data()["total_market_cap"]
    snapshot_id = _save_snapshot(coins, total_cap)
    invalidate_coin_history()
    _cache_analytics()
    return snapshot_id
