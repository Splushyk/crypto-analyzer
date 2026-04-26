"""
Интеграционные тесты Celery-задачи сбора снимка и её API-эндпоинта.
Тесты выполняются в eager-режиме: задача отрабатывает синхронно,
без реального Redis и воркера. Провайдер данных замокирован.
"""

import pytest
from requests.exceptions import ConnectionError
from rest_framework.test import APIClient

from crypto.models import CoinPrice, Snapshot
from crypto.tasks import fetch_snapshot_task


@pytest.mark.django_db
def test_fetch_snapshot_task_success(mocker, sample_coin):
    """Задача успешно получает данные от провайдера и сохраняет снимок в БД."""
    mock_provider = mocker.Mock()
    mock_provider.get_coins.return_value = [sample_coin]
    mocker.patch("crypto.tasks._build_provider", return_value=mock_provider)

    result = fetch_snapshot_task.delay("coingecko")

    assert result.successful()
    assert Snapshot.objects.count() == 1
    assert CoinPrice.objects.count() == 1

    snapshot = Snapshot.objects.first()
    assert snapshot is not None
    assert snapshot.id == result.result

    price = CoinPrice.objects.first()
    assert price is not None
    assert price.symbol == sample_coin.symbol
    assert price.snapshot == snapshot


@pytest.mark.django_db
def test_fetch_snapshot_task_retries_on_api_error(mocker, sample_coin, settings):
    """
    При временной сетевой ошибке задача повторяет попытку и в итоге успешно завершается.
    """
    # Celery при retry бросает Retry-исключение. С EAGER_PROPAGATES=True оно
    # пробросится наружу на первой же попытке, не дав механизму retry отработать.
    settings.CELERY_TASK_EAGER_PROPAGATES = False

    mock_provider = mocker.Mock()
    mock_provider.get_coins.side_effect = [
        ConnectionError("API недоступен"),
        ConnectionError("API недоступен"),
        [sample_coin],
    ]
    mocker.patch("crypto.tasks._build_provider", return_value=mock_provider)
    mocker.patch("time.sleep")

    result = fetch_snapshot_task.delay("coingecko")

    assert result.successful()
    # API вызвался 3 раза (1 изначальная + 2 retry)
    assert mock_provider.get_coins.call_count == 3
    assert Snapshot.objects.count() == 1


@pytest.mark.django_db
def test_fetch_snapshot_endpoint_returns_202_with_task_id(mocker, admin_client):
    """
    POST на эндпоинт запуска задачи возвращает 202 Accepted и task_id.
    Задача не выполняется по-настоящему: мокаем .delay на уровне view,
    проверяем только контракт эндпоинта. Эндпоинт требует staff-прав,
    поэтому используется admin_client.
    """
    mock_delay = mocker.patch("crypto.views.fetch_snapshot_task.delay")
    mock_delay.return_value.id = "fake-task-id"

    response = admin_client.post("/api/v1/tasks/fetch-snapshot/", {}, format="json")

    assert response.status_code == 202
    assert response.data["task_id"] == "fake-task-id"
    mock_delay.assert_called_once_with("coingecko")


def test_fetch_snapshot_endpoint_unauthorized_for_anonymous(mocker):
    """
    Анонимный запрос на эндпоинт запуска задачи получает 401.
    Celery-задача при этом не должна планироваться.
    """
    mock_delay = mocker.patch("crypto.views.fetch_snapshot_task.delay")

    client = APIClient()
    response = client.post("/api/v1/tasks/fetch-snapshot/", {}, format="json")

    assert response.status_code == 401
    mock_delay.assert_not_called()


@pytest.mark.django_db
def test_fetch_snapshot_endpoint_forbidden_for_regular_user(mocker, auth_client_a):
    """
    Обычный аутентифицированный пользователь без is_staff получает 403.
    Celery-задача при этом не должна планироваться.
    """
    mock_delay = mocker.patch("crypto.views.fetch_snapshot_task.delay")

    response = auth_client_a.post("/api/v1/tasks/fetch-snapshot/", {}, format="json")

    assert response.status_code == 403
    mock_delay.assert_not_called()
