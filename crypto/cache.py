from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from rest_framework.serializers import Serializer

# TTL чуть больше интервала Beat (раз в час) - кеш не протухнет между запусками.
ANALYTICS_CACHE_TTL = 60 * 70

CACHE_KEY_MARKET_STATS = "market_stats"
CACHE_KEY_TOP_MOVERS = "top_movers"
CACHE_KEY_VOLUME_LEADERS = "volume_leaders"


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
