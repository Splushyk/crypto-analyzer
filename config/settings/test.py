"""Настройки для тестового окружения (pytest)."""

import fakeredis

from config.settings.base import *  # noqa: F403

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"

# В тестах используется тот же django-redis бэкенд, что в проде, но через fakeredis
# (in-memory имитация Redis). Это даёт нативный delete_pattern и поведение,
# совпадающее с продакшеном, без зависимости от живого Redis-сервера.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://fake/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "connection_class": fakeredis.FakeRedisConnection,
            },
        },
    }
}

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
DATABASES["default"]["HOST"] = "127.0.0.1"  # noqa: F405
