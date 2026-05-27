"""Настройки для production-окружения."""

import sentry_sdk
from django.http import Http404
from rest_framework.exceptions import NotFound, Throttled
from sentry_sdk.types import Event, Hint

from config.settings.base import *  # noqa: F403

DEBUG = False

# Очередь python-logstash-async на SQLite, переживает рестарт контейнера.
# Volume <service>_logstash_queue смонтирован на /var/lib/logstash-async/ в compose;
# каждый сервис (web, celery-worker, celery-beat) имеет свой volume, потому что
# одна SQLite-БД не может обслуживать несколько процессов одновременно.
LOGGING["handlers"]["logstash"]["database_path"] = (  # type: ignore[index]  # noqa: F405
    "/var/lib/logstash-async/queue.db"
)

SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405


def _before_send(event: Event, hint: Hint) -> Event | None:
    exc_info = hint.get("exc_info")
    if exc_info:
        exc = exc_info[1]
        if isinstance(exc, (Http404, NotFound, Throttled)):
            return None
    return event


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment="production",
        send_default_pii=True,
        traces_sample_rate=0.0,
        before_send=_before_send,
    )
