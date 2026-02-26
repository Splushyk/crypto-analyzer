import requests
import time
from rich.table import Table
from rich.console import Console
from datetime import datetime
import json
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()

url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"


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


@retry(max_attempts=3, delay=2)
def get_crypto_data(site):
    """
    Отправляет запрос к API.

    :param site: Адрес запроса.
    :return: Список словарей с данными по каждой монете.
    """
    response = requests.get(site, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data


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
        key=lambda x: x.get(key) or 0,
        reverse=reverse
    )[:n]


def analyze_data(data):
    """
    Анализирует список словарей монет.

    :param data: Список словарей с данными о монетах.
    :return: Кортеж из найденных целевых данных:
        top_up - топ-3 лидера роста за 24 часа,
        top_down - топ-3 лидера падения за 24 часа,
        max_value - монета с максимальным объёмом торгов,
        total_market_cap - суммарная капитализация всех 50 монет.
    """
    top_price_change = [coin for coin in data
                        if coin["price_change_percentage_24h"] is not None]

    top_up = get_top_coins(top_price_change, "price_change_percentage_24h")
    top_down = get_top_coins(top_price_change, "price_change_percentage_24h", reverse=False)

    max_value = get_top_coins(data, "total_value", n=1)[0]
    total_market_cap = sum(coin.get("market_cap") or 0 for coin in data)

    return top_up, top_down, max_value, total_market_cap


def display_results(
        top_up,
        top_down,
        max_value,
        total_market_cap
):
    """
    Выводит результаты в красивом виде на экран.

    :param top_up: Топ-3 лидера роста за 24 часа.
    :param top_down: Топ-3 лидера падения за 24 часа.
    :param max_value: Монета с максимальным объёмом торгов.
    :param total_market_cap: Суммарная капитализация всех 50 монет.
    :return: None.
    """
    table_up = Table(title="Топ монеты (рост)")
    table_up.add_column("Название", style="cyan")
    table_up.add_column("Рост", style="green")
    for coin in top_up:
        table_up.add_row(coin["name"], f"+{coin["price_change_percentage_24h"]}")

    console.print(table_up)

    table_down = Table(title="Топ монеты (падение)")
    table_down.add_column("Название", style="cyan")
    table_down.add_column("Падение", style="red")
    for coin in top_down:
        table_down.add_row(coin["name"], f"{coin["price_change_percentage_24h"]}")

    console.print(table_down)

    console.print(
        f"\n[bold white]Монета с максимальным объёмом:[/bold white] {max_value["name"]} — ${max_value["total_value"]:,.0f}")
    console.print(f"[bold white]Суммарная капитализация топ-50:[/bold white] ${total_market_cap:,.0f}")


def save_report(top_up, top_down, max_value, total_market_cap):
    """
    Сохраняет отчет в файл формата json.

    :param top_up: Топ-3 лидера роста за 24 часа.
    :param top_down: Топ-3 лидера падения за 24 часа.
    :param max_value: Монета с максимальным объёмом торгов.
    :param total_market_cap: Суммарная капитализация всех 50 монет.
    :return: None.
    """
    required_keys = ["name", "symbol", "price_change_percentage_24h"]
    date = datetime.now()

    report = {
        "generated_at": date.strftime("%Y-%m-%d %H-%M-%S"),
        "total_coins_analyzed": 50,
        "total_market_cap_usd": total_market_cap,
        "top_gainers": [
            {key: value for key, value in coin.items()
             if key in required_keys}
            for coin in top_up
        ],
        "top_losers": [
            {key: value for key, value in coin.items()
             if key in required_keys}
            for coin in top_down
        ],
        "highest_value": {key: value for key, value in max_value.items() if
                           key in ["name", "symbol", "total_value"]}
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
        coins = get_crypto_data(url)

    top_up, top_down, max_val, total_cap = analyze_data(coins)
    display_results(top_up, top_down, max_val, total_cap)
    save_report(top_up, top_down, max_val, total_cap)

except requests.exceptions.RequestException as e:
    logger.error(f"Не удалось загрузить данные: {e}")
