"""Настройки для тестового окружения (pytest)."""

from config.settings.base import *  # noqa: F403

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"

# Тесты не зависят от Redis - pytest однопроцессный.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
DATABASES["default"]["HOST"] = "127.0.0.1"  # noqa: F405
