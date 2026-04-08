"""
Модуль тестирования компонентов визуализации данных (Console, JSON, CSV).

Ключевые проверки:
1. Полиморфизм интерфейсов: проверка того, что все классы поддерживают единый метод `display`.
2. Изоляция побочных эффектов: мокирование системных вызовов `builtins.open` и вывода в консоль `rich.console`.
3. Валидация логики формирования контента:
   - Проверка структуры и формата JSON-отчета.
   - Тестирование временных меток с использованием `freezegun`.
   - Проверка корректности имен файлов и кодировок при записи.
4. Edge Cases: устойчивость визуализаторов к отсутствию данных в выборках.

Тесты гарантируют корректное представление проанализированных данных в различных форматах.
"""

import json
import pytest
from freezegun import freeze_time

from src.visualizers import ConsoleVisualizer, JsonVisualizer, CsvVisualizer


@pytest.fixture
def sample_results(sample_coin):
    return {
        "top_up": [sample_coin],
        "top_down": [sample_coin],
        "max_volume": sample_coin,
        "total_market_cap": 777.12345
    }


# Маппинг: какой класс какой системный инструмент использует
VISUALIZER_METRICS = {
    "ConsoleVisualizer": "rich.console.Console.print",
    "JsonVisualizer": "builtins.open",
    "CsvVisualizer": "builtins.open",
}


@pytest.mark.parametrize("visualizer_class", [
    ConsoleVisualizer,
    JsonVisualizer,
    CsvVisualizer,
])
def test_visualizers_interface_polymorphism(visualizer_class, sample_results, mocker):
    """Тест проверяет полиморфизм: единый интерфейс display для всех классов."""

    # 1. Инициализация
    instance = visualizer_class()
    target = VISUALIZER_METRICS[visualizer_class.__name__]

    # 2. Мокаем инструмент (open для файлов или print для консоли)
    if "open" in target:
        mocked_tool = mocker.patch(target, mocker.mock_open())
    else:
        mocked_tool = mocker.patch(target)

    # 3. Act (вызов через единый интерфейс)
    instance.display(sample_results)

    # 4. Assert
    assert mocked_tool.called, f"Ошибка в {visualizer_class.__name__}"


@pytest.mark.parametrize("visualizer_class", [
    ConsoleVisualizer,
    JsonVisualizer,
    CsvVisualizer,
])
def test_visualizers_edge_cases_empty_data(visualizer_class, sample_coin, mocker):
    """Проверка всех визуализаторов на пустых данных (Edge Case)."""

    # 1. Готовим "минимальные" данные
    empty_results = {
        "top_up": [],  # Пустой список
        "top_down": [],
        "max_volume": sample_coin,
        "total_market_cap": 0
    }

    instance = visualizer_class()

    # 2. Мокаем всё сразу, чтобы тест не лез в реальные файлы/консоль
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("rich.console.Console.print")

    # 3. Действие: вызываем display.
    # Проверяем, что display не падает на пустых списках top_up и top_down
    instance.display(empty_results)


@freeze_time("2026-03-16 10:00:00")
def test_json_visualizer_content_logic(sample_results, mocker):
    """Проверка содержимого JSON: структура и корректность данных."""
    m = mocker.mock_open()
    mocker.patch("builtins.open", m)

    viz = JsonVisualizer("test.json")
    viz.display(sample_results)

    # Проверяем, что записано именно то, что нужно
    mock_file = m()
    written_data = "".join(call.args[0] for call in mock_file.write.call_args_list)
    data = json.loads(written_data)

    assert data["total_market_cap_usd"] == 777.12345
    assert data["generated_at"] == "2026-03-16 10-00-00"
    assert data["top_gainers"][0]["name"] == "SomeCoin"


def test_visualizer_custom_filenames(sample_results, mocker):
    """Проверка соответствия имен файлов."""
    m = mocker.patch("builtins.open", mocker.mock_open())

    JsonVisualizer("test.json").display(sample_results)
    m.assert_any_call("test.json", "w", encoding="utf-8")

    CsvVisualizer("test.csv").display(sample_results)
    m.assert_any_call("test.csv", mode="w", newline="", encoding="utf-8")
