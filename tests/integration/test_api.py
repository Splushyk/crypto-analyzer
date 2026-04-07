import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_snapshots_list_is_paginated(snapshots):
    client = APIClient()
    response = client.get('/api/snapshots/')
    assert response.status_code == 200  # проверяем результат
    assert response.data['count'] == 3
    assert response.data['next'] is not None
    assert len(response.data['results']) == 2


@pytest.mark.django_db
def test_coin_price_history(coins):
    client = APIClient()
    response = client.get('/api/coins/?symbol=C1')
    assert response.status_code == 200
    assert response.data['count'] == 2
