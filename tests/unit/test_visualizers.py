"""
Модуль тестирования консольного визуализатора.
Гарантирует корректное отображение проанализированных данных в терминале.
"""

import pytest
from src.visualizers import ConsoleVisualizer



def test_console_visualizer_display_calls_print(sample_results, mocker):
    """
    Проверка вывода основного анализа в консоль.
    Убеждаемся, что метод display обращается к библиотеке rich для печати таблиц.
    """
    # 1. Arrange
    # Мокаем метод print у Console из библиотеки rich
    mock_print = mocker.patch("rich.console.Console.print")
    instance = ConsoleVisualizer()

    # 2. Act
    instance.display(sample_results)

    # 3. Assert
    assert mock_print.called, "Метод display должен вызывать печать в консоль"


def test_visualizers_edge_cases_empty_data(sample_coin, mocker):
    """Проверка визуализатора на пустых данных."""

    # 1. Готовим "минимальные" данные
    empty_results = {
        "top_up": [],  # Пустой список
        "top_down": [],
        "max_volume": sample_coin,
        "total_market_cap": 0
    }
    mock_print = mocker.patch("rich.console.Console.print")
    instance = ConsoleVisualizer()

    # 2. Act и Assert (проверяем, что не вылетает исключение)
    try:
        instance.display(empty_results)
    except Exception as e:
        pytest.fail(f"ConsoleVisualizer - ошибка на пустых данных: {e}")

    assert mock_print.called


def test_display_snapshots_calls_print(mocker):
    """Проверка вывода списка снимков из БД."""
    # 1. Готовим фейковые данные (как они приходят из БД)
    fake_snapshots = [
        {'id': 1, 'created_at': '2026-03-24 12:00', 'total_market_cap': 1000000.0},
        {'id': 2, 'created_at': '2026-03-24 13:00', 'total_market_cap': 1200000.0}
    ]
    mock_print = mocker.patch("rich.console.Console.print")
    viz = ConsoleVisualizer()

    # 2. Act
    viz.display_snapshots(fake_snapshots)

    # 3. Assert
    assert mock_print.called, "Метод display_snapshots должен вызывать rich.print"


def test_display_comparison_calls_print(mocker):
    """Проверка вывода таблицы сравнения двух снимков."""
    # 1. Данные для сравнения
    fake_comparison = [
        {
            'symbol': 'SC',
            'old_price': 60000.0,
            'new_price': 61000.0,
            'percent_change': 1.66
        }
    ]
    mock_print = mocker.patch("rich.console.Console.print")
    viz = ConsoleVisualizer()

    # 2. Act
    viz.display_comparison(fake_comparison, id1=1, id2=2)

    # 3. Assert
    assert mock_print.called, "Метод display_comparison должен вызывать rich.print"
