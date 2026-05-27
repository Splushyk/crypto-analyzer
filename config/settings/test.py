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

# В тестах не отправляем логи в Logstash: DNS-имя `logstash` доступно только
# внутри docker-сети, а pytest бежит на хосте. Оставляем только console handler.
del LOGGING["handlers"]["logstash"]  # type: ignore[attr-defined]  # noqa: F405
LOGGING["root"]["handlers"] = ["console"]  # type: ignore[index]  # noqa: F405
LOGGING["loggers"]["django_redis.cache"]["handlers"] = ["console"]  # type: ignore[index]  # noqa: F405
