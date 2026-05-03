"""
Модуль тестирования парсеров данных различных провайдеров.

Ключевые проверки:
1. Корректность трансформации сырого JSON (от Gecko и CMC) в объекты Cryptocurrency.
2. Проверка идентичности полей (цена, объем, капитализация) после парсинга.
3. Валидация типов данных: убеждаемся, что парсер возвращает список объектов моделей.
4. Обработка пустых ответов: проверка возврата пустого списка вместо генерации ошибок.

Используется параметризация для тестирования всех парсеров в рамках единого сценария.
"""

import pytest

from src.models import Cryptocurrency
from src.parsers import CMCParser, GeckoParser


@pytest.mark.parametrize(
    "parser_class, data_fixture",
    [
        (GeckoParser, "gecko_raw_data"),
        (CMCParser, "cmc_raw_data"),
    ],
    ids=["Gecko", "CMC"],
)
def test_parsers_work_correctly(parser_class, data_fixture, request, sample_coin):
    raw_data = request.getfixturevalue(data_fixture)
    result = parser_class().parse(raw_data)

    assert len(result) == 1
    assert isinstance(result[0], Cryptocurrency)
    assert result[0] == sample_coin


@pytest.mark.parametrize("parser_class", [GeckoParser, CMCParser])
def test_parsers_empty_data(parser_class):
    result = parser_class().parse([])
    assert result == []
