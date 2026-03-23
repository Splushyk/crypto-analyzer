"""
Модуль отвечает за отображение результатов анализа.
"""

import csv
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)


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
    """Подтверждает сохранение результатов анализа в JSON-файл."""

    def __init__(self):
        self.console = Console()

    def display(self, results: dict):
        self.console.print("Данные сохранены в JSON")


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
