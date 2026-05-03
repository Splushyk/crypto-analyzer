"""
Точка входа в приложение и координация рабочих процессов.

Модуль отвечает за:
1. Конфигурацию CLI-интерфейса (на базе Typer).
2. Инициализацию компонентов через фабричные методы (Providers, Visualizers, Storages).
3. Управление основным циклом программы:
   получение данных -> анализ -> вывод -> сохранение.
4. Централизованную обработку исключений и логирование ошибок.
"""

import logging
import os
from collections.abc import Callable

import typer
from dotenv import load_dotenv
from rich.console import Console

from src.analyzer import CryptoAnalyzer
from src.api_client import ApiClient
from src.parsers import CMCParser, GeckoParser
from src.providers import CMCProvider, CryptoProvider, GeckoProvider
from src.settings import StorageType, settings
from src.storage import AnalyticsStorage, BaseStorage, JsonStorage, SqliteStorage
from src.visualizers import BaseVisualizer, ConsoleVisualizer

load_dotenv()

app = typer.Typer()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

console = Console()

PROVIDERS: dict[str, Callable[[], CryptoProvider]] = {
    "coingecko": lambda: GeckoProvider(
        client=ApiClient(base_url="https://api.coingecko.com/api/v3/coins/markets"),
        parser=GeckoParser(),
    ),
    "coinmarketcap": lambda: CMCProvider(
        client=ApiClient(
            base_url="https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            headers={"X-CMC_PRO_API_KEY": os.getenv("CMC_API_KEY")},
        ),
        parser=CMCParser(),
    ),
}

VISUALIZERS: dict[str, Callable[[], BaseVisualizer]] = {
    "console": lambda: ConsoleVisualizer(),
}

STORAGES: dict[StorageType, Callable[[], BaseStorage]] = {
    StorageType.JSON: lambda: JsonStorage(),
    StorageType.SQLITE: lambda: SqliteStorage(),
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

    :param output: Формат вывода ('console').
    :return: Экземпляр визуализатора.
    :raises ValueError: Если передан неизвестный формат.
    """
    if output not in VISUALIZERS:
        raise ValueError(f"Вывод возможен в форматах: {', '.join(VISUALIZERS)}")
    return VISUALIZERS[output]()


def build_storage() -> BaseStorage:
    """
    Фабричная функция для создания хранилища данных.

    : return: Экземпляр хранилища.
    """
    return STORAGES[settings.storage]()


@app.command()
def run(
    source: str = typer.Option(
        "coingecko", help="Источник данных: coingecko или coinmarketcap"
    ),
    output: str = typer.Option("console", help="Формат вывода: console"),
    top: int = typer.Option(
        3, min=1, max=50, help="Количество лидеров роста и падения (от 1 до 50)"
    ),
):
    """
    Точка входа CLI.
    Загружает данные, анализирует, отображает результаты и сохраняет их.
    """
    provider = build_provider(source)
    visualizer = build_visualizer(output)

    with build_storage() as storage:
        try:
            with console.status("Загружаем данные..."):
                coins = provider.get_coins()
            analyzer = CryptoAnalyzer(coins)
            results = analyzer.analyze_data(top)

            # Показываем результат (консоль)
            visualizer.display(results)

            # Сохраняем в базу (SQLite или JSON-базу)
            storage.save(coins, results)

        except Exception as e:
            logger.error(f"Произошла ошибка при работе с данными: {e}")


@app.command()
def list_snapshots():
    """Выводит список всех сохранённых снимков с датой и временем."""
    # Нам нужен именно консольный визуализатор для таблиц
    visualizer = ConsoleVisualizer()

    with build_storage() as storage:
        if not isinstance(storage, AnalyticsStorage):
            logger.error("Выбранный тип хранилища не поддерживает просмотр снимков.")
            raise typer.Exit(code=1)

        try:
            snapshots = storage.get_all_snapshots()
            if not snapshots:
                logger.warning("База данных пуста.")
                return
            visualizer.display_snapshots(snapshots)
        except Exception as e:
            logger.error(f"Ошибка при получении списка снимков: {e}")


@app.command()
def compare_snapshots(id1: int, id2: int):
    """Сравнивает два снимка по ID (например: compare 1 5)."""
    visualizer = ConsoleVisualizer()

    with build_storage() as storage:
        if not isinstance(storage, AnalyticsStorage):
            logger.error("Это хранилище не поддерживает сравнение.")
            raise typer.Exit(code=1)

        try:
            diff = storage.get_snapshot_compare(id1, id2)
            if not diff:
                logger.warning(f"Данные для снимков {id1} и {id2} не найдены.")
                return
            visualizer.display_comparison(diff, id1, id2)
        except Exception as e:
            logger.error(f"Ошибка при сравнении снимков: {e}")


if __name__ == "__main__":
    app()
