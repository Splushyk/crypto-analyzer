"""
Точка входа в приложение и координация рабочих процессов.

Модуль отвечает за:
1. Конфигурацию CLI-интерфейса (на базе Typer).
2. Инициализацию компонентов через фабричные методы (Providers, Visualizers, Storages).
3. Управление основным циклом программы: получение данных -> анализ -> вывод -> сохранение.
4. Централизованную обработку исключений и логирование ошибок.
"""

import logging
import os
from collections.abc import Callable

import typer
from rich.console import Console

from src.api_client import ApiClient
from src.analyzer import CryptoAnalyzer
from src.parsers import GeckoParser, CMCParser
from src.providers import CryptoProvider, GeckoProvider, CMCProvider
from src.storage import BaseStorage, JsonStorage
from src.visualizers import BaseVisualizer, ConsoleVisualizer, JsonVisualizer, CsvVisualizer
from src.settings import settings, StorageType

app = typer.Typer()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()

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
    "json": lambda: JsonVisualizer(),
    "csv": lambda: CsvVisualizer(filename="crypto_report.csv"),
}

STORAGES: dict[StorageType, Callable[[], BaseStorage]] = {
    StorageType.JSON: lambda: JsonStorage(),
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


def build_storage() -> BaseStorage:
    """
    Фабричная функция для создания хранилища данных.

    : return: Экземпляр хранилища.
    """
    return STORAGES[settings.storage]()


@app.command()
def main(
        source: str = typer.Option("coingecko", help="Источник данных: coingecko или coinmarketcap"),
        output: str = typer.Option("console", help="Формат вывода: console, json или csv"),
        top: int = typer.Option(3, min=1, max=50, help="Количество лидеров роста и падения (от 1 до 50)")
):
    """
    Точка входа CLI. Загружает данные, анализирует, отображает результаты и сохраняет их.
    """
    provider = build_provider(source)
    visualizer = build_visualizer(output)
    storage = build_storage()

    try:
        with console.status("Загружаем данные..."):
            coins = provider.get_coins()
        analyzer = CryptoAnalyzer(coins)
        results = analyzer.analyze_data(top)
        visualizer.display(results)
        storage.save(results)
    except Exception as e:
        logger.error(f"Произошла ошибка при работе с данными: {e}")


if __name__ == "__main__":
    app()
