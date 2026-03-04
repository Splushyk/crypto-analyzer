import requests
import time
from rich.table import Table
from rich.console import Console
from datetime import datetime
import json
from functools import wraps
import logging
from abc import abstractmethod, ABC

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
    @abstractmethod
    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        """Принимает сырой список словарей и возвращает список объектов Cryptocurrency"""
        pass


class GeckoParser(BaseParser):
    def parse(self, raw_data: list) -> list[Cryptocurrency]:
        # Мы берем данные из словаря (item.get) и создаем объект нашего класса
        return [
            Cryptocurrency(
                name=item.get("name"),
                symbol=item.get("symbol"),
                price=item.get("current_price"),
                change_24h=item.get("price_change_percentage_24h"),
                volume=item.get("total_volume"),
                market_cap=item.get("market_cap")
            )
            for item in raw_data
        ]


class ApiClient:
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
    @abstractmethod
    def get_coins(self) -> list[Cryptocurrency]:
        """Должен вернуть список объектов Cryptocurrency"""
        pass


class GeckoProvider(CryptoProvider):
    def __init__(self):
        # Вся конфигурация Gecko живет здесь
        self.url = "https://api.coingecko.com/api/v3/coins/markets"
        self.params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1
        }
        self.client = ApiClient(base_url=self.url)
        self.parser = GeckoParser()

    def get_coins(self) -> list[Cryptocurrency]:
        # Менеджер дает команды курьеру и упаковщику
        raw_data = self.client.get_json(params=self.params)
        return self.parser.parse(raw_data)


def get_top_coins(data, key, n=3, reverse=True):
    """
    Возвращает список из n монет, отсортированных по заданному ключу.

    :param data: Список словарей с данными о монетах.
    :param key: Ключ, по которому происходит сортировка.
    :param n: Количество монет в результате. По умолчанию 3.
    :param reverse: Порядок сортировки. True — по убыванию, False — по возрастанию.
    :return: Список из n словарей.
    """
    return sorted(
        data,
        key=lambda x: getattr(x, key) or 0,
        reverse=reverse
    )[:n]


def analyze_data(data):
    """
    Анализирует список словарей монет.

    :param data: Список словарей с данными о монетах.
    :return: Кортеж из найденных целевых данных:
        top_up - топ-3 лидера роста за 24 часа,
        top_down - топ-3 лидера падения за 24 часа,
        max_volume - монета с максимальным объёмом торгов,
        total_market_cap - суммарная капитализация всех 50 монет.
    """
    top_up = get_top_coins(data, "change_24h")
    top_down = get_top_coins(data, "change_24h", reverse=False)

    max_volume_coin = get_top_coins(data, "volume", n=1)[0]
    total_market_cap = sum(coin.market_cap for coin in data)

    return top_up, top_down, max_volume_coin, total_market_cap


def display_results(
        top_up,
        top_down,
        max_volume,
        total_market_cap
):
    """
    Выводит результаты в красивом виде на экран.

    :param top_up: Топ-3 лидера роста за 24 часа.
    :param top_down: Топ-3 лидера падения за 24 часа.
    :param max_volume: Монета с максимальным объёмом торгов.
    :param total_market_cap: Суммарная капитализация всех 50 монет.
    :return: None.
    """
    table_up = Table(title="Топ монеты (рост)")
    table_up.add_column("Название", style="cyan")
    table_up.add_column("Рост", style="green")
    for coin in top_up:
        table_up.add_row(coin.name, f"+{coin.change_24h:.2f}%")

    console.print(table_up)

    table_down = Table(title="Топ монеты (падение)")
    table_down.add_column("Название", style="cyan")
    table_down.add_column("Падение", style="red")
    for coin in top_down:
        table_down.add_row(coin.name, f"{coin.change_24h:.2f}%")

    console.print(table_down)

    console.print(
        f"\n[bold white]Монета с максимальным объёмом:[/bold white] {max_volume.name} — ${max_volume.volume:,.0f}")
    console.print(f"[bold white]Суммарная капитализация топ-50:[/bold white] ${total_market_cap:,.0f}")


def save_report(top_up, top_down, max_volume, total_market_cap):
    """
    Сохраняет отчет в файл формата json.

    :param top_up: Топ-3 лидера роста за 24 часа.
    :param top_down: Топ-3 лидера падения за 24 часа.
    :param max_volume: Монета с максимальным объёмом торгов.
    :param total_market_cap: Суммарная капитализация всех 50 монет.
    :return: None.
    """
    required_keys = ["name", "symbol", "price_change_percentage_24h"]
    date = datetime.now()

    report = {
        "generated_at": date.strftime("%Y-%m-%d %H-%M-%S"),
        "total_market_cap_usd": total_market_cap,
        "top_gainers": [
            {"name": c.name, "symbol": c.symbol, "change_24h": c.change_24h}
            for c in top_up
        ],
        "top_losers": [
            {"name": c.name, "symbol": c.symbol, "change_24h": c.change_24h}
            for c in top_down
        ],
        "highest_volume": {
            "name": max_volume.name,
            "symbol": max_volume.symbol,
            "volume": max_volume.volume
        }
    }

    with open("crypto_report.json", "w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )


top_up = top_down = max_val = total_cap = None

try:
    with console.status("Загружаем данные..."):
        # Создаем одного провайдера (директора)
        provider = GeckoProvider()

        # Просим его дать готовые монеты.
        # Он сам внутри себя создаст ApiClient, скачает JSON и отдаст его в GeckoParser.
        coins = provider.get_coins()

    top_up, top_down, max_val, total_cap = analyze_data(coins)
    display_results(top_up, top_down, max_val, total_cap)
    save_report(top_up, top_down, max_val, total_cap)

except Exception as e:  # Меняем на общий Exception, так как ошибка может быть и в сети, и в парсинге
    logger.error(f"Произошла ошибка при работе с данными: {e}")
