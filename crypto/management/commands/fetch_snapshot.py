from django.core.management.base import BaseCommand

from crypto.tasks import fetch_snapshot_task


class Command(BaseCommand):
    help = 'Запускает Celery-задачу сбора снимка рынка'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='coingecko',
            help='Источник данных: coingecko или cmc'
        )

    def handle(self, *args, **options):
        source = options['source'].lower()
        result = fetch_snapshot_task.delay(source)
        self.stdout.write(f"Задача запущена: task_id={result.id}")
