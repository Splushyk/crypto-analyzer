"""
Сервисный слой для работы с watchlist.
Содержит бизнес-логику: валидация символа через API биржи,
управление списком отслеживаемых монет пользователя.
Не зависит от DRF — работает только с Django ORM и стандартной библиотекой.
"""

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Avg, Max, Min, QuerySet, Sum

from crypto.exceptions import SymbolNotFoundOnExchangeError, WatchlistDuplicateError
from crypto.models import CoinPrice, Snapshot, WatchlistItem
from src.api_client import ApiClient


def _get_latest_snapshot_prices() -> QuerySet[CoinPrice]:
    """
    Queryset цен последнего снимка рынка. Если снимков ещё нет — возвращает
    гарантированно пустой queryset (CoinPrice.objects.none()), чтобы вызывающий
    код не различал «снимков нет» и «снимок есть, но пустой».
    """
    latest_snapshot = Snapshot.objects.order_by("-created_at").first()
    if latest_snapshot is None:
        return CoinPrice.objects.none()
    return CoinPrice.objects.filter(snapshot=latest_snapshot)


def get_market_stats() -> dict[str, float] | None:
    """
    Агрегированная статистика цен по последнему снимку рынка.
    Возвращает словарь с min/max/avg цены и суммой капитализации,
    либо None, если нет ни одного снимка или снимок пустой.
    """
    stats = _get_latest_snapshot_prices().aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
        avg_price=Avg("price"),
        total_market_cap=Sum("market_cap"),
    )

    if stats["min_price"] is None:
        return None

    return stats


def get_top_movers() -> dict[str, QuerySet[CoinPrice, CoinPrice]] | None:
    """
    Топ-5 растущих и топ-5 падающих монет по change_24h за последний снимок.
    Возвращает словарь с двумя querysets, либо None, если нет ни одного снимка
    или последний снимок пустой.
    """
    prices = _get_latest_snapshot_prices()
    if not prices.exists():
        return None

    return {
        "top_gainers": prices.order_by("-change_24h")[:5],
        "top_losers": prices.order_by("change_24h")[:5],
    }


def get_volume_leaders() -> dict[str, QuerySet[CoinPrice, CoinPrice]] | None:
    """
    Топ-10 монет по объёму торгов за последний снимок.
    Возвращает словарь с queryset, либо None, если нет ни одного снимка
    или последний снимок пустой.
    """
    prices = _get_latest_snapshot_prices()
    if not prices.exists():
        return None

    return {
        "leaders": prices.order_by("-volume")[:10],
    }


def get_user_watchlist(user: User) -> QuerySet[WatchlistItem, WatchlistItem]:
    """Возвращает все монеты из watchlist пользователя."""
    return WatchlistItem.objects.filter(user=user)


def remove_from_watchlist(user: User, symbol: str) -> bool:
    """
    Удаляет монету из watchlist.
    Возвращает True если удалена, False если не найдена.
    """
    deleted_item = WatchlistItem.objects.filter(user=user, symbol=symbol).delete()
    return True if deleted_item[0] == 1 else False


def _validate_coingecko(symbol: str) -> tuple[str, str]:
    """Проверяет существование символа через CoinGecko API."""
    client = ApiClient(base_url="https://api.coingecko.com/api/v3")
    data = client.get_json(endpoint="/search", params={"query": symbol})

    for coin in data["coins"]:
        if coin["symbol"] == symbol.upper():
            return coin["symbol"], coin["name"]

    raise SymbolNotFoundOnExchangeError


def _validate_cmc(symbol: str) -> tuple[str, str]:
    """Проверяет существование символа через CoinMarketCap API."""
    client = ApiClient(
        base_url="https://pro-api.coinmarketcap.com/v1",
        headers={"X-CMC_PRO_API_KEY": os.getenv("CMC_API_KEY")},
    )
    data = client.get_json(
        endpoint="/cryptocurrency/map",
        params={"symbol": symbol.upper()},
    )

    for coin in data.get("data", []):
        if coin["symbol"] == symbol.upper():
            return coin["symbol"], coin["name"]

    raise SymbolNotFoundOnExchangeError


VALIDATORS = {
    "coingecko": _validate_coingecko,
    "coinmarketcap": _validate_cmc,
}


def validate_symbol(symbol: str) -> tuple[str, str]:
    """
    Проверяет существование символа через API выбранной биржи.
    Возвращает (symbol, name).
    """
    provider = settings.CRYPTO_PROVIDER
    validator = VALIDATORS.get(provider)

    if validator is None:
        raise ValueError(f"Неизвестный провайдер: {provider}")

    return validator(symbol)


def add_to_watchlist(user: User, symbol: str) -> WatchlistItem:
    """Валидирует символ и добавляет монету в watchlist пользователя."""
    coin_info = validate_symbol(symbol)

    try:
        item = WatchlistItem.objects.create(
            user=user,
            symbol=coin_info[0],
            coin_name=coin_info[1],
        )
    except IntegrityError:
        raise WatchlistDuplicateError

    return item
