"""
Тесты интерфейса командной строки (CLI) и логики запуска приложения.
Используются моки для изоляции бизнес-логики и проверки обработки аргументов Typer.
"""

import pytest
from typer.testing import CliRunner
import src.main
from src.main import app
from src.providers import CMCProvider, GeckoProvider
from src.visualizers import CsvVisualizer, JsonVisualizer, ConsoleVisualizer

runner = CliRunner()


@pytest.fixture
def mock_dependencies(mocker, sample_coin):
    mock_provider = mocker.Mock()
    mock_provider.get_coins.return_value = [sample_coin]
    mocker.patch("src.main.build_provider", return_value=mock_provider)

    mock_results = {
        "top_up": [sample_coin],
        "top_down": [sample_coin],
        "max_volume": sample_coin,
        "total_market_cap": 1000.0
    }
    mock_analyzer_inst = mocker.Mock()
    mock_analyzer_inst.analyze_data.return_value = mock_results
    mocker.patch("src.main.CryptoAnalyzer", return_value=mock_analyzer_inst)

    mock_visualizer = mocker.Mock()
    mocker.patch("src.main.build_visualizer", return_value=mock_visualizer)

    return {
        "provider": mock_provider,
        "visualizer": mock_visualizer,
        "analyzer": mock_analyzer_inst
    }


def test_main_success_flow(mock_dependencies):
    result = runner.invoke(app, ["--source", "coingecko", "--output", "console"])
    assert result.exit_code == 0
    mock_dependencies["provider"].get_coins.assert_called_once()
    mock_dependencies["visualizer"].display.assert_called_once()


def test_main_invalid_source():
    """Проверка ошибки при неверном источнике данных."""
    # Используем catch_exceptions=False, чтобы увидеть реальную ошибку
    with pytest.raises(ValueError) as excinfo:
        runner.invoke(app, ["--source", "unknown_api"], catch_exceptions=False)

    assert "Выбор возможен между" in str(excinfo.value)


def test_main_invalid_output():
    """Проверка ошибки при неверном формате вывода (покрытие ошибки в build_visualizer)."""
    # Вызываем через runner, ожидаем ValueError из-за логики в build_visualizer
    with pytest.raises(ValueError) as excinfo:
        runner.invoke(app, ["--output", "pdf"], catch_exceptions=False)

    assert "Вывод возможен в форматах: console, json, csv" in str(excinfo.value)


@pytest.mark.parametrize("source", ["coingecko", "coinmarketcap"])
def test_main_sources_dispatch(source, mock_dependencies, mocker):
    spy_build = mocker.spy(src.main, "build_provider")
    runner.invoke(app, ["--source", source])
    spy_build.assert_called_with(source)


def test_main_error_handling(mocker, caplog):
    """Проверка логирования ошибок."""
    mock_provider = mocker.Mock()
    mock_provider.get_coins.side_effect = Exception("API Error")
    mocker.patch("src.main.build_provider", return_value=mock_provider)

    # В main.py ошибка ловится внутри try/except, поэтому exit_code будет 0
    with caplog.at_level("ERROR"):
        result = runner.invoke(app, ["--source", "coingecko"])

    assert result.exit_code == 0
    assert "Произошла ошибка при работе с данными: API Error" in caplog.text


def test_main_top_argument_passing(mock_dependencies):
    """Проверка проброса параметра --top в анализатор."""
    runner.invoke(app, ["--top", "10"])

    # Проверяем позиционный аргумент, как он передается в main.py
    mock_dependencies["analyzer"].analyze_data.assert_called_once_with(10)


@pytest.mark.parametrize("source, expected_class", [
    ("coingecko", GeckoProvider),
    ("coinmarketcap", CMCProvider),
])
def test_build_provider_returns_correct_type(source, expected_class):
    """Проверка, что фабрика провайдеров возвращает нужные классы."""
    # Обращаемся через src.main, так как функции определены там
    provider = src.main.build_provider(source)
    assert isinstance(provider, expected_class)


@pytest.mark.parametrize("output, expected_class", [
    ("console", ConsoleVisualizer),
    ("json", JsonVisualizer),
    ("csv", CsvVisualizer),
])
def test_build_visualizer_returns_correct_type(output, expected_class):
    """Проверка, что фабрика визуализаторов возвращает нужные классы."""
    visualizer = src.main.build_visualizer(output)
    assert isinstance(visualizer, expected_class)


def test_build_visualizer_parameters():
    """Проверка параметров инициализации визуализаторов."""
    json_viz = src.main.build_visualizer("json")
    csv_viz = src.main.build_visualizer("csv")

    assert json_viz.filename == "crypto_report.json"
    assert csv_viz.filename == "crypto_report.csv"
