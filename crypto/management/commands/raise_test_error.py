from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Raise a RuntimeError to verify Sentry error reporting."

    def handle(self, *args, **options):
        raise RuntimeError("Sentry connectivity test")
