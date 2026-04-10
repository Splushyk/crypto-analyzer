"""
Сервисный слой для работы с watchlist.
Содержит бизнес-логику: валидация символа через API биржи, управление списком отслеживаемых монет пользователя.
Не зависит от DRF — работает только с Django ORM и стандартной библиотекой.
"""

import os

from django.conf import settings
from django.db import IntegrityError

from crypto.models import WatchlistItem
from src.api_client import ApiClient


class SymbolNotFoundError(Exception):
    """Символ не найден на бирже."""
    pass


class ExistInWatchlistError(Exception):
    """Монета уже есть в watchlist пользователя."""
    pass


def get_user_watchlist(user):
    """Возвращает все монеты из watchlist пользователя."""
    return WatchlistItem.objects.filter(user=user)


def remove_from_watchlist(user, symbol):
    """Удаляет монету из watchlist. Возвращает True если удалена, False если не найдена."""
    deleted_item = WatchlistItem.objects.filter(user=user, symbol=symbol).delete()
    return True if deleted_item[0] == 1 else False


def _validate_coingecko(symbol):
    """Проверяет существование символа через CoinGecko API."""
    client = ApiClient(base_url="https://api.coingecko.com/api/v3")
    data = client.get_json(endpoint="/search", params={"query": symbol})

    for coin in data["coins"]:
        if coin["symbol"] == symbol.upper():
            return coin["symbol"], coin["name"]

    raise SymbolNotFoundError


def _validate_cmc(symbol):
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

    raise SymbolNotFoundError


VALIDATORS = {
    "coingecko": _validate_coingecko,
    "coinmarketcap": _validate_cmc,
}


def validate_symbol(symbol):
    """Проверяет существование символа через API выбранной биржи. Возвращает (symbol, name)."""
    provider = settings.CRYPTO_PROVIDER
    validator = VALIDATORS.get(provider)

    if validator is None:
        raise ValueError(f"Неизвестный провайдер: {provider}")

    return validator(symbol)


def add_to_watchlist(user, symbol):
    """Валидирует символ и добавляет монету в watchlist пользователя."""
    coin_info = validate_symbol(symbol)

    try:
        item = WatchlistItem.objects.create(
            user=user,
            symbol=coin_info[0],
            coin_name=coin_info[1],
        )
    except IntegrityError:
        raise ExistInWatchlistError

    return item
