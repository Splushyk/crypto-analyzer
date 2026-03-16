"""
Модуль содержит интеграционные тесты для провайдеров данных.
Провайдеры выделены в интеграционный слой, так как их основная задача —
корректное взаимодействие между сетевым клиентом и парсером данных.
"""

import pytest
from src.providers import GeckoProvider, CMCProvider


@pytest.mark.parametrize("provider_class, data_fixture, transform_func", [
    # Для Gecko данные идут как есть (просто возвращаем их)
    (GeckoProvider, "gecko_raw_data", lambda d: d),
    # Для CMC данные приходят в словаре под ключом "data"
    (CMCProvider, "cmc_raw_data", lambda d: {"data": d}),
], ids=["CoinGecko", "CoinMarketCap"])
def test_providers_data_flow(provider_class, data_fixture, transform_func, request, mocker):
    """
    Универсальный тест потока данных:
    Проверяет, что провайдер правильно запрашивает данные и передает их в парсер.
    """
    # 1. Arrange
    raw_data = request.getfixturevalue(data_fixture)
    mock_client = mocker.Mock()
    mock_parser = mocker.Mock()

    # Имитируем ответ API, упаковывая данные из фикстуры нужным образом
    mock_client.get_json.return_value = transform_func(raw_data)
    mock_parser.parse.return_value = ["MockedCoin"]

    provider = provider_class(mock_client, mock_parser)

    # 2. Action
    result = provider.get_coins()

    # 3. Assert - проверяем, что в парсер ушел чистый список из фикстуры
    mock_parser.parse.assert_called_once_with(raw_data)
    assert result == ["MockedCoin"]


def test_cmc_provider_handles_missing_data_key(mocker):
    """
    Edge Case: проверка специфической логики CMC (отсутствие ключа 'data').
    Этот тест вынесен отдельно, так как он проверяет уникальный защитный механизм.
    """
    mock_client = mocker.Mock()
    mock_parser = mocker.Mock()

    mock_client.get_json.return_value = {}  # Пустой ответ без ключа 'data'

    provider = CMCProvider(mock_client, mock_parser)
    provider.get_coins()

    # Должен передать пустой список в парсер, а не упасть
    mock_parser.parse.assert_called_once_with([])
