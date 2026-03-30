import os

from django.core.management.base import BaseCommand
from crypto.models import Snapshot, CoinPrice

from src.api_client import ApiClient
from src.parsers import GeckoParser, CMCParser
from src.providers import GeckoProvider, CMCProvider
from src.analyzer import CryptoAnalyzer


class Command(BaseCommand):
    help = 'Запрашивает данные с выбранного API и сохраняет в БД'

    def add_arguments(self, parser):
        # Добавляем возможность выбирать источник через флаг --source
        parser.add_argument(
            '--source',
            type=str,
            default='coingecko',
            help='Источник данных: coingecko или cmc'
        )

    def handle(self, *args, **options):
        source = options['source'].lower()
        self.stdout.write(f"Выбран источник: {source}")

        try:
            if source == 'coingecko':
                client = ApiClient(base_url="https://api.coingecko.com/api/v3/coins/markets")
                parser = GeckoParser()
                provider = GeckoProvider(client=client, parser=parser)

            elif source == 'cmc':
                # Для CMC берем ключ из .env
                api_key = os.getenv("CMC_API_KEY")
                if not api_key:
                    raise ValueError("Не найден CMC_API_KEY в переменных окружения!")

                client = ApiClient(
                    base_url="https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
                    headers={"X-CMC_PRO_API_KEY": api_key}
                )
                parser = CMCParser()
                provider = CMCProvider(client=client, parser=parser)
            else:
                self.stdout.write(self.style.ERROR(f"Неизвестный источник: {source}"))
                return

            # Далее логика одинаковая для обоих провайдеров
            coins = provider.get_coins()
            analyzer = CryptoAnalyzer(coins)
            total_cap = analyzer.analyze_data()['total_market_cap']

            snapshot = Snapshot.objects.create(total_market_cap=total_cap)

            coin_price_objects = [
                CoinPrice(
                    snapshot=snapshot,
                    name=c.name,
                    symbol=c.symbol,
                    price=c.price,
                    change_24h=c.change_24h,
                    volume=c.volume,
                    market_cap=c.market_cap
                ) for c in coins
            ]

            CoinPrice.objects.bulk_create(coin_price_objects)
            self.stdout.write(self.style.SUCCESS(f"Готово! Данные из {source} сохранены."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
