"""
Модуль тестирования низкоуровневого API-клиента.

Основные проверки:
1. Корректность инициализации клиента и настройки HTTP-заголовков.
2. Изоляция сетевых запросов через мокирование объектов requests.Session.
3. Тестирование механизма повторных запросов (retry logic):
   - Проверка количества попыток при таймаутах и ошибках соединения.
   - Валидация логирования предупреждений при каждой неудачной попытке.
4. Параметризация тестов для проверки различных типов сетевых исключений.
"""

import pytest
import requests

from src.api_client import ApiClient


@pytest.mark.parametrize("base_url, headers", [
    ("https://fake-api.com", {"Some_item": "some_value"}),
    ("https://fake-api.com", None),
])
def test_api_client_headers(base_url, headers):
    client = ApiClient(base_url, headers)
    assert client.headers["Accept"] == "application/json"


def test_get_json(mock_session, mock_response, api_client):
    mock_session.get.return_value = mock_response

    assert api_client.get_json() == {"some_item": "some_value"}


@pytest.mark.parametrize("exc", [
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
])
def test_get_json_exceptions(mock_session, api_client, mocker, exc, caplog):
    mocker.patch("src.api_client.time.sleep")

    mock_session.get.side_effect = exc

    with pytest.raises(exc):
        with caplog.at_level("WARNING"):
            api_client.get_json()

    assert mock_session.get.call_count == 3
    assert "Ошибка сети (попытка 1/3)" in caplog.text
    assert "Ошибка сети (попытка 2/3)" in caplog.text
