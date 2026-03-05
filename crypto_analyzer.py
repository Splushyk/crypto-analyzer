import csv
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from functools import wraps
import requests
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

app = typer.Typer()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()


def retry(max_attempts, delay):
    """
    Декоратор, который оборачивает функцию логикой повторных попыток.

    :param max_attempts: Количество попыток до того, как будет выброшено исключение.
    :param delay: Время ожидания в секундах между попытками.
    :return: Результат выполнения оборачиваемой функции.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    return result
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"Достигнуто максимальное количество попыток. Ошибка: {e}")
                        raise

                    logger.warning(f"Ошибка сети (попытка {attempt + 1}/{max_attempts}). Ждем {delay} сек...")
                    time.sleep(delay)

        return wrapper

    return decorator


class Cryptocurrency:
    """Представляет криптовалюту с основными рыночными данными."""

    def __init__(self, name: str, symbol: str, price: float, change_24h: float, volume: float, market_cap: float):
        self.name = name
        self.symbol = symbol.upper()
        self.price = price or 0.0
        self.change_24h = change_24h or 0.0  # Защита от None
        self.volume = volume or 0.0
        self.market_cap = market_cap or 0.0

    def __str__(self):
        return f"{self.name} ({self.symbol}): ${self.price:,.2f} ({self.change_24h:+.2f}%)"

    def __lt__(self, other):
        if not isinstance(other, Cryptocurrency):
            return NotImplemented
        return self.change_24h < other.change_24h


class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров сырых данных API."""

    @abstractmethod
    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        """Принимает сырой список словарей и возвращает список объектов Cryptocurrency"""
        pass


class GeckoParser(BaseParser):
    """Парсер для данных CoinGecko API."""

    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        # Мы берем данные из словаря (item.get) и создаем объект нашего класса
        return [
            Cryptocurrency(
                name=item.get("name"),
                symbol=item.get("symbol"),
                price=item.get("current_price", 0),
                change_24h=item.get("price_change_percentage_24h", 0),
                volume=item.get("total_volume", 0),
                market_cap=item.get("market_cap", 0)
            )
            for item in raw_data
        ]


class CMCParser(BaseParser):
    """Парсер для данных CoinMarketCap API."""

    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        return [
            Cryptocurrency(
                name=item.get("name"),
                symbol=item.get("symbol"),
                price=usd.get("price", 0),
                change_24h=usd.get("percent_change_24h", 0),
                volume=usd.get("volume_24h", 0),
                market_cap=usd.get("market_cap", 0)
            )
            for item in raw_data
            if (usd := item.get("quote", {}).get("USD", {}))
        ]


class ApiClient:
    """HTTP-клиент для выполнения GET-запросов к API."""

    def __init__(self, base_url: str, headers: dict | None = None):
        self.base_url = base_url
        # Если заголовки не переданы, используем пустой словарь
        self.headers = headers or {}
        # Добавляем стандартный заголовок, если его нет
        if "Accepts" not in self.headers:
            self.headers["Accepts"] = "application/json"

    @retry(max_attempts=3, delay=2)
    def get_json(self, endpoint: str = "", params: dict | None = None):
        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()


class CryptoProvider(ABC):
    """Абстрактный базовый класс для провайдеров криптовалютных данных."""

    @abstractmethod
    def get_coins(self) -> list[Cryptocurrency]:
        """Должен вернуть список объектов Cryptocurrency"""
        pass


class GeckoProvider(CryptoProvider):
    """Провайдер данных CoinGecko. Получает топ-50 монет по капитализации."""

    def __init__(self, client: ApiClient, parser: BaseParser):
        self.params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1
        }
        self.client = client
        self.parser = parser

    def get_coins(self) -> list[Cryptocurrency]:
        raw_data = self.client.get_json(params=self.params)
        coins = self.parser.parse(raw_data)
        logger.info(f"Получено {len(coins)} монет от CoinGecko")
        return coins


class CMCProvider(CryptoProvider):
    """Провайдер данных CoinMarketCap. Требует API-ключ в переменной окружения CMC_API_KEY."""

    def __init__(self, client: ApiClient, parser: BaseParser):
        self.client = client
        self.parser = parser

    def get_coins(self) -> list[Cryptocurrency]:
        params = {
            "start": "1",
            "limit": "50",
            "convert": "USD"
        }
        raw_response = self.client.get_json(params=params)
        coins_list = raw_response.get("data", [])
        logger.info(f"Получено {len(coins_list)} монет от CoinMarketCap")
        return self.parser.parse(coins_list)


class CryptoAnalyzer:
    """Анализирует список криптовалют: топ роста, падения, объёма и капитализации."""

    def __init__(self, data: list[Cryptocurrency]):
        self.data = data

    def get_top_coins(self, attr: str, n: int = 3, reverse: bool = True):
        """Внутренний метод для сортировки объектов по любому атрибуту"""
        return sorted(
            self.data,
            key=lambda x: getattr(x, attr) or 0,
            reverse=reverse
        )[:n]

    def analyze_data(self, top: int = 3):
        """Основной метод, который возвращает словарь со всеми расчетами"""
        top_up = self.get_top_coins("change_24h", n=top)
        top_down = self.get_top_coins("change_24h", n=top, reverse=False)
        max_volume = self.get_top_coins("volume", n=1)[0]
        total_market_cap = sum(coin.market_cap for coin in self.data)

        return {
            "top_up": top_up,
            "top_down": top_down,
            "max_volume": max_volume,
            "total_market_cap": total_market_cap
        }


class BaseVisualizer(ABC):
    """Абстрактный базовый класс для отображения результатов анализа."""

    @abstractmethod
    def display(self, results: dict):
        """Метод для отображения результатов анализа"""
        pass


class ConsoleVisualizer(BaseVisualizer):
    """Выводит результаты анализа в консоль в виде таблиц."""

    def __init__(self):
        self.console = Console()

    def display(self, results: dict):
        # 1. Таблица лидеров роста
        table_up = Table(title="Топ монеты (рост)")
        table_up.add_column("Название", style="cyan")
        table_up.add_column("Рост", style="green")
        for coin in results["top_up"]:
            table_up.add_row(coin.name, f"+{coin.change_24h:.2f}%")
        self.console.print(table_up)

        # 2. Таблица лидеров падения
        table_down = Table(title="Топ монеты (падение)")
        table_down.add_column("Название", style="cyan")
        table_down.add_column("Падение", style="red")
        for coin in results["top_down"]:
            table_down.add_row(coin.name, f"{coin.change_24h:.2f}%")
        self.console.print(table_down)

        # 3. Общая информация
        max_vol = results["max_volume"]
        total_cap = results["total_market_cap"]
        self.console.print(f"\n[bold white]Макс. объём:[/bold white] {max_vol.name} — ${max_vol.volume:,.0f}")
        self.console.print(f"[bold white]Капитализация топ-50:[/bold white] ${total_cap:,.0f}")


class JsonVisualizer(BaseVisualizer):
    """Сохраняет результаты анализа в JSON-файл."""

    def __init__(self, filename: str = "crypto_report.json"):
        self.filename = filename

    def display(self, results: dict):
        date = datetime.now()

        report = {
            "generated_at": date.strftime("%Y-%m-%d %H-%M-%S"),
            "total_market_cap_usd": results["total_market_cap"],
            "top_gainers": [
                {"name": c.name, "symbol": c.symbol, "change_24h": c.change_24h}
                for c in results["top_up"]
            ],
            "top_losers": [
                {"name": c.name, "symbol": c.symbol, "change_24h": c.change_24h}
                for c in results["top_down"]
            ],
            "highest_volume": {
                "name": results["max_volume"].name,
                "symbol": results["max_volume"].symbol,
                "volume": results["max_volume"].volume
            }
        }

        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        logger.info(f"Отчет успешно сохранен в JSON-файл: {self.filename}")


class CsvVisualizer(BaseVisualizer):
    """Сохраняет результаты анализа в CSV-файл."""

    def __init__(self, filename: str = "crypto_report.csv"):
        self.filename = filename

    def display(self, results: dict):
        categories = [
            (results["top_up"], "Gainer"),
            (results["top_down"], "Loser")
        ]

        with open(self.filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            # Записываем шапку
            writer.writerow(["Name", "Symbol", "Type", "Price", "Change 24h", "Market Cap"])

            for coins_list, category_name in categories:
                for coin in coins_list:
                    writer.writerow([
                        coin.name,
                        coin.symbol,
                        category_name,
                        f"{coin.price:.2f}",
                        f"{coin.change_24h:.2f}",
                        f"{coin.market_cap:.0f}"
                    ])

        logger.info(f"Отчет успешно сохранен в CSV-файл: {self.filename}")


PROVIDERS: dict[str, Callable[[], CryptoProvider]] = {
    "coingecko": lambda: GeckoProvider(
        client=ApiClient(base_url="https://api.coingecko.com/api/v3/coins/markets"),
        parser=GeckoParser()
    ),
    "coinmarketcap": lambda: CMCProvider(
        client=ApiClient(
            base_url="https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            headers={"X-CMC_PRO_API_KEY": os.getenv("CMC_API_KEY")}
        ),
        parser=CMCParser()
    ),
}

VISUALIZERS: dict[str, Callable[[], BaseVisualizer]] = {
    "console": lambda: ConsoleVisualizer(),
    "json": lambda: JsonVisualizer(filename="crypto_report.json"),
    "csv": lambda: CsvVisualizer(filename="crypto_report.csv"),
}


def build_provider(source: str) -> CryptoProvider:
    """
    Фабричная функция для создания провайдера данных.

    :param source: Источник данных ('coingecko' или 'coinmarketcap').
    :return: Экземпляр провайдера.
    :raises ValueError: Если передан неизвестный источник.
    """
    if source not in PROVIDERS:
        raise ValueError(f"Выбор возможен между: {', '.join(PROVIDERS)}")
    return PROVIDERS[source]()


def build_visualizer(output: str) -> BaseVisualizer:
    """
    Фабричная функция для создания визуализатора.

    :param output: Формат вывода ('console', 'json' или 'csv').
    :return: Экземпляр визуализатора.
    :raises ValueError: Если передан неизвестный формат.
    """
    if output not in VISUALIZERS:
        raise ValueError(f"Вывод возможен в форматах: {', '.join(VISUALIZERS)}")
    return VISUALIZERS[output]()

@app.command()
def main(
    source: str = typer.Option("coingecko", help="Источник данных: coingecko или coinmarketcap"),
    output: str = typer.Option("console", help="Формат вывода: console, json или csv"),
    top: int = typer.Option(3, help="Количество лидеров роста и падения")
):
    """
    Точка входа CLI. Загружает данные, анализирует и отображает результаты.
    """
    provider = build_provider(source)
    visualizer = build_visualizer(output)

    try:
        with console.status("Загружаем данные..."):
            coins = provider.get_coins()
        analyzer = CryptoAnalyzer(coins)
        results = analyzer.analyze_data(top)
        visualizer.display(results)
    except Exception as e:
        logger.error(f"Произошла ошибка при работе с данными: {e}")


if __name__ == "__main__":
    app()
