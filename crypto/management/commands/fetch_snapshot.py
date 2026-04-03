import os

from django.core.management.base import BaseCommand
from django.db import DatabaseError
from requests.exceptions import RequestException

from crypto.models import Snapshot, CoinPrice
from src.api_client import ApiClient
from src.parsers import GeckoParser, CMCParser
from src.providers import GeckoProvider, CMCProvider
from src.analyzer import CryptoAnalyzer

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"


class Command(BaseCommand):
    help = 'Запрашивает данные с выбранного API и сохраняет в БД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='coingecko',
            help='Источник данных: coingecko или cmc'
        )

    def _build_provider(self, source):
        if source == 'coingecko':
            return GeckoProvider(
                client=ApiClient(base_url=COINGECKO_URL),
                parser=GeckoParser()
            )
        if source == 'cmc':
            api_key = os.getenv("CMC_API_KEY")
            if not api_key:
                raise ValueError("Не найден CMC_API_KEY в переменных окружения!")
            return CMCProvider(
                client=ApiClient(
                    base_url=CMC_URL,
                    headers={"X-CMC_PRO_API_KEY": api_key}
                ),
                parser=CMCParser()
            )
        raise ValueError(f"Неизвестный источник: {source}")

    def _save_snapshot(self, coins, total_cap):
        snapshot = Snapshot.objects.create(total_market_cap=total_cap)
        CoinPrice.objects.bulk_create([
            CoinPrice(
                snapshot=snapshot,
                name=c.name,
                symbol=c.symbol,
                price=c.price,
                change_24h=c.change_24h,
                volume=c.volume,
                market_cap=c.market_cap
            ) for c in coins
        ])

    def handle(self, *args, **options):
        source = options['source'].lower()
        self.stdout.write(f"Выбран источник: {source}")

        try:
            provider = self._build_provider(source)
            coins = provider.get_coins()
            total_cap = CryptoAnalyzer(coins).analyze_data()['total_market_cap']
            self._save_snapshot(coins, total_cap)
            self.stdout.write(self.style.SUCCESS(f"Готово! Данные из {source} сохранены."))

        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Ошибка конфигурации: {e}"))
        except RequestException as e:
            self.stdout.write(self.style.ERROR(f"Ошибка сети: {e}"))
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f"Ошибка базы данных: {e}"))
