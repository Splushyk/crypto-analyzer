"""
Health-check эндпоинт `/health/` для систем мониторинга.
Проверяет доступность БД, кеша (Redis) и Celery broker - возвращает 200 или 503.
"""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

from config.celery import app as celery_app

_HEALTHCHECK_CACHE_KEY = "healthcheck:probe"
_HEALTHCHECK_CACHE_VALUE = "ok"


def _check_db() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def _check_cache() -> bool:
    try:
        cache.set(_HEALTHCHECK_CACHE_KEY, _HEALTHCHECK_CACHE_VALUE, timeout=5)
        return cache.get(_HEALTHCHECK_CACHE_KEY) == _HEALTHCHECK_CACHE_VALUE
    except Exception:
        return False


def _check_celery() -> bool:
    try:
        return bool(celery_app.control.inspect(timeout=1).ping())
    except Exception:
        return False


def health(request) -> JsonResponse:
    checks = {
        "db": "ok" if _check_db() else "fail",
        "cache": "ok" if _check_cache() else "fail",
        "celery": "ok" if _check_celery() else "fail",
    }
    healthy = all(value == "ok" for value in checks.values())
    return JsonResponse(
        {
            "status": "ok" if healthy else "degraded",
            "checks": checks,
        },
        status=200 if healthy else 503,
    )
