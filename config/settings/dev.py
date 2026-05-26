"""Настройки для локальной разработки."""

from config.settings.base import *  # noqa: F403

DEBUG = True

INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

# За nginx Django видит IP контейнера-прокси, а не клиента -> стандартный
# IP-фильтр debug-toolbar не срабатывает. В dev показываем тулбар всегда,
# когда DEBUG=True (никакая прод-логика на этой настройке не висит).
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

# Цветной structlog ConsoleRenderer вместо JSON для удобства локальной разработки.
LOGGING["handlers"]["console"]["formatter"] = "console"  # type: ignore[index]  # noqa: F405
