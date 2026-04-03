"""
Тесты интерфейса командной строки (CLI) и логики запуска приложения.
Используются моки для изоляции бизнес-логики и проверки обработки аргументов Typer.
"""

import pytest
from typer.testing import CliRunner
import src.main
from src.main import app
from src.storage import AnalyticsStorage
from src.providers import CMCProvider, GeckoProvider

pytestmark = pytest.mark.unit
runner = CliRunner()


@pytest.fixture
def mock_dependencies(mocker, sample_coin):
    mock_provider = mocker.Mock()
    mock_provider.get_coins.return_value = [sample_coin]
    mocker.patch("src.main.build_provider", return_value=mock_provider)

    mock_storage = mocker.Mock(spec=AnalyticsStorage)
    mock_storage.__enter__ = mocker.Mock(return_value=mock_storage)
    mock_storage.__exit__ = mocker.Mock(return_value=False)
    mocker.patch("src.main.build_storage", return_value=mock_storage)

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
        "analyzer": mock_analyzer_inst,
        "storage": mock_storage
    }


def test_run_success_flow(mock_dependencies):
    result = runner.invoke(app, ["run", "--source", "coingecko", "--output", "console"])
    assert result.exit_code == 0
    mock_dependencies["provider"].get_coins.assert_called_once()
    mock_dependencies["visualizer"].display.assert_called_once()
    mock_dependencies["storage"].save.assert_called_once()


def test_run_invalid_source():
    """Проверка ошибки при неверном источнике данных."""
    # Используем catch_exceptions=False, чтобы увидеть реальную ошибку
    with pytest.raises(ValueError) as excinfo:
        runner.invoke(app, ["run", "--source", "unknown_api"], catch_exceptions=False)

    assert "Выбор возможен между" in str(excinfo.value)


def test_run_invalid_output():
    """Проверка ошибки при неверном формате вывода (покрытие ошибки в build_visualizer)."""
    # Вызываем через runner, ожидаем ValueError из-за логики в build_visualizer
    with pytest.raises(ValueError) as excinfo:
        runner.invoke(app, ["run", "--output", "pdf"], catch_exceptions=False)

    assert "Вывод возможен в форматах: console" in str(excinfo.value)


@pytest.mark.parametrize("source", ["coingecko", "coinmarketcap"])
def test_run_sources_dispatch(source, mock_dependencies, mocker):
    spy_build = mocker.spy(src.main, "build_provider")
    runner.invoke(app, ["run", "--source", source])
    spy_build.assert_called_with(source)


def test_run_error_handling(mock_dependencies, caplog):
    """Проверка логирования ошибок."""
    mock_dependencies["provider"].get_coins.side_effect = Exception("API Error")

    with caplog.at_level("ERROR"):
        runner.invoke(app, ["run", "--source", "coingecko"])

    assert "Произошла ошибка при работе с данными: API Error" in caplog.text


def test_run_top_argument_passing(mock_dependencies):
    """Проверка проброса параметра --top в анализатор."""
    runner.invoke(app, ["run", "--top", "10"])

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


def test_build_visualizer_console():
    """Проверка, что фабрика возвращает консольный визуализатор."""
    from src.visualizers import ConsoleVisualizer
    visualizer = src.main.build_visualizer("console")
    assert isinstance(visualizer, ConsoleVisualizer)


def test_main_list_snapshots_success(mock_dependencies, mocker):
    """Проверка успешного вывода списка снимков."""
    # 1. Даем полные данные, чтобы цикл в визуализаторе не сломался
    fake_data = [{'id': 1, 'created_at': '2026-03-24', 'total_market_cap': 1000}]
    mock_dependencies["storage"].get_all_snapshots.return_value = fake_data

    # 2. Мокаем сам КЛАСС визуализатора, так как он создается внутри функции
    mock_viz_class = mocker.patch("src.main.ConsoleVisualizer")

    result = runner.invoke(app, ["list-snapshots"])

    assert result.exit_code == 0
    # Проверяем вызов через инстанс, который создал сам mocker.patch
    mock_viz_class.return_value.display_snapshots.assert_called_once()


def test_main_compare_success(mock_dependencies, mocker):
    """Проверка успешного сравнения двух снимков."""
    # Данные для сравнения (символы, цены и т.д.)
    fake_diff = [{
        'symbol': 'BTC', 'old_price': 100, 'new_price': 110, 'percent_change': 10
    }]
    mock_dependencies["storage"].get_snapshot_compare.return_value = fake_diff

    # Мокаем класс визуализатора локально
    mock_viz_class = mocker.patch("src.main.ConsoleVisualizer")

    result = runner.invoke(app, ["compare-snapshots", "1", "2"])

    assert result.exit_code == 0
    mock_viz_class.return_value.display_comparison.assert_called_once()


def test_build_storage_factory(mocker):
    """Проверка фабрики build_storage."""
    # 1. Мокаем настройки, чтобы функция всегда видела SQLITE
    mock_settings = mocker.patch("src.main.settings")
    from src.main import StorageType
    mock_settings.storage = StorageType.SQLITE

    # 2. Мокаем сам словарь STORAGES, чтобы он вернул наш мок-объект
    mock_storage_obj = mocker.Mock()
    mocker.patch("src.main.STORAGES", {StorageType.SQLITE: lambda: mock_storage_obj})

    # 3. Вызываем
    storage = src.main.build_storage()

    # 4. Проверяем, что получили именно наш мок
    assert storage == mock_storage_obj


def test_list_snapshots_empty_db(mock_dependencies, caplog):
    """Проверка случая, когда в базе нет снимков."""
    mock_dependencies["storage"].get_all_snapshots.return_value = []

    with caplog.at_level("WARNING"):
        runner.invoke(app, ["list-snapshots"])

    assert "База данных пуста" in caplog.text


def test_list_snapshots_error_logging(mock_dependencies, caplog):
    """Проверка логирования ошибки при падении БД."""
    mock_dependencies["storage"].get_all_snapshots.side_effect = Exception("DB Crash")

    with caplog.at_level("ERROR"):
        runner.invoke(app, ["list-snapshots"])

    assert "Ошибка при получении списка снимков: DB Crash" in caplog.text


def test_compare_snapshots_not_found(mock_dependencies, caplog):
    """Проверка случая, когда снимки для сравнения не найдены."""
    mock_dependencies["storage"].get_snapshot_compare.return_value = None

    with caplog.at_level("WARNING"):
        runner.invoke(app, ["compare-snapshots", "999", "1000"])

    assert "Данные для снимков 999 и 1000 не найдены" in caplog.text
