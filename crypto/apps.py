from django.apps import AppConfig


class CryptoConfig(AppConfig):
    name = "crypto"

    def ready(self):
        from crypto import signals  # noqa: F401
