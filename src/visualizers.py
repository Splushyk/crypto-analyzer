"""
Модуль отвечает за отображение результатов анализа.
"""

import logging
from abc import ABC, abstractmethod

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

    def display_snapshots(self, snapshots: list[dict]):
        """Вывод списка всех снимков."""
        table = Table(title="[bold blue]Архив снимков рынка[/bold blue]")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Дата", style="magenta")
        table.add_column("Капитализация", justify="right", style="green")

        for s in snapshots:
            table.add_row(str(s['id']), s['created_at'], f"${s['total_market_cap']:,.0f}")

        self.console.print(table)

    def display_comparison(self, comparison: list[dict], id1: int, id2: int):
        """Сравнение двух снимков."""
        table = Table(title=f"[bold blue]Сравнение снимков #{id1} и #{id2}[/bold blue]")
        table.add_column("Символ", style="cyan")
        table.add_column("Старая цена")
        table.add_column("Новая цена")
        table.add_column("Изменение", justify="right")

        for row in comparison:
            color = "green" if row['percent_change'] > 0 else "red"
            table.add_row(
                row['symbol'],
                f"${row['old_price']:.6f}",
                f"${row['new_price']:.6f}",
                f"[{color}]{row['percent_change']:+.2f}%[/{color}]"
            )
        self.console.print(table)


