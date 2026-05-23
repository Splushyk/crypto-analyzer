from collections.abc import Callable
from typing import Any, cast

from django.core.cache import cache
from django_redis.cache import RedisCache  # type: ignore[import-untyped]
from rest_framework.serializers import Serializer

# TTL чуть больше интервала Beat (раз в час) - кеш не протухнет между запусками.
ANALYTICS_CACHE_TTL = 60 * 70
COIN_HISTORY_CACHE_TTL = 60 * 70
WATCHLIST_CACHE_TTL = 60 * 5

CACHE_KEY_MARKET_STATS = "market_stats"
CACHE_KEY_TOP_MOVERS = "top_movers"
CACHE_KEY_VOLUME_LEADERS = "volume_leaders"

# Префикс для ключей истории цен. Полный ключ:
# coin_history_{symbol}_{cursor}_{min_price}_{max_price}
# Сносится по паттерну при появлении нового снимка.
CACHE_KEY_PREFIX_COIN_HISTORY = "coin_history"

# Префикс для per-user ключей watchlist. Полный ключ: watchlist_{user_id}.
CACHE_KEY_PREFIX_WATCHLIST = "watchlist"

# Префикс для per-user ключей портфеля. Полный ключ: portfolio_{user_id}.
# Сносится при buy/sell конкретного юзера и при появлении нового снимка
# (тогда у всех юзеров поменялась текущая цена -> все ключи невалидны).
CACHE_KEY_PREFIX_PORTFOLIO = "portfolio"
PORTFOLIO_CACHE_TTL = 60 * 70  # с запасом > часа beat-расписания


def invalidate_coin_history() -> None:
    """Сносит весь кеш истории цен - данные изменились с появлением нового снимка."""
    cast(RedisCache, cache).delete_pattern(f"{CACHE_KEY_PREFIX_COIN_HISTORY}_*")


def watchlist_cache_key(user_id: int) -> str:
    return f"{CACHE_KEY_PREFIX_WATCHLIST}_{user_id}"


def invalidate_watchlist(user_id: int) -> None:
    """Сносит кеш watchlist конкретного пользователя - после add/remove."""
    cache.delete(watchlist_cache_key(user_id))


def portfolio_cache_key(user_id: int) -> str:
    return f"{CACHE_KEY_PREFIX_PORTFOLIO}_{user_id}"


def portfolio_history_cache_key(user_id: int) -> str:
    return f"{CACHE_KEY_PREFIX_PORTFOLIO}_history_{user_id}"


def invalidate_portfolio(user_id: int) -> None:
    """Сносит кеш портфеля и истории конкретного юзера после buy/sell."""
    cache.delete_many(
        [portfolio_cache_key(user_id), portfolio_history_cache_key(user_id)]
    )


def invalidate_all_portfolios() -> None:
    """
    Сносит кеш портфеля у всех юзеров: после нового снимка цены
    поменялись для всех, все ключи невалидны.
    """
    cast(RedisCache, cache).delete_pattern(f"{CACHE_KEY_PREFIX_PORTFOLIO}_*")


def cache_aside(
    key: str,
    computer: Callable[[], Any],
    serializer_cls: type[Serializer],
    ttl: int = ANALYTICS_CACHE_TTL,
    many: bool = False,
) -> Any:
    """
    Cache-aside: вернуть закешированное или посчитать, сериализовать, закешировать.
    Возвращает None, если computer вернул None (нет данных).
    many=True — для коллекций (queryset/list), сериализатор получит many=True.
    """
    cached = cache.get(key)
    if cached is not None:
        return cached

    obj = computer()
    if obj is None:
        return None
    data = serializer_cls(obj, many=many).data
    cache.set(key, data, ttl)
    return data
