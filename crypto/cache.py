from collections.abc import Callable
from typing import Any, cast

from django.core.cache import cache
from django_redis.cache import RedisCache  # type: ignore[import-untyped]
from rest_framework.serializers import Serializer

# TTL чуть больше интервала Beat (раз в час) - кеш не протухнет между запусками.
ANALYTICS_CACHE_TTL = 60 * 70
COIN_HISTORY_CACHE_TTL = 60 * 70

CACHE_KEY_MARKET_STATS = "market_stats"
CACHE_KEY_TOP_MOVERS = "top_movers"
CACHE_KEY_VOLUME_LEADERS = "volume_leaders"

# Префикс для ключей истории цен. Полный ключ:
# coin_history_{symbol}_{cursor}_{min_price}_{max_price}
# Сносится по паттерну при появлении нового снимка.
CACHE_KEY_PREFIX_COIN_HISTORY = "coin_history"


def invalidate_coin_history() -> None:
    """Сносит весь кеш истории цен - данные изменились с появлением нового снимка."""
    cast(RedisCache, cache).delete_pattern(f"{CACHE_KEY_PREFIX_COIN_HISTORY}_*")


def cache_aside(
    key: str,
    computer: Callable[[], Any],
    serializer_cls: type[Serializer],
    ttl: int = ANALYTICS_CACHE_TTL,
) -> Any:
    """
    Cache-aside: вернуть закешированное или посчитать, сериализовать, закешировать.
    Возвращает None, если computer вернул None (нет данных).
    """
    cached = cache.get(key)
    if cached is not None:
        return cached

    obj = computer()
    if obj is None:
        return None
    data = serializer_cls(obj).data
    cache.set(key, data, ttl)
    return data
