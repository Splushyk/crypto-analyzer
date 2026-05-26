"""Настройки для production-окружения."""

from config.settings.base import *  # noqa: F403

DEBUG = False

# Очередь python-logstash-async на SQLite, переживает рестарт контейнера.
# Volume <service>_logstash_queue смонтирован на /var/lib/logstash-async/ в compose;
# каждый сервис (web, celery-worker, celery-beat) имеет свой volume, потому что
# одна SQLite-БД не может обслуживать несколько процессов одновременно.
LOGGING["handlers"]["logstash"]["database_path"] = (  # type: ignore[index]  # noqa: F405
    "/var/lib/logstash-async/queue.db"
)
