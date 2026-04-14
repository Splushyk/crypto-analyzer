import pytest
from django.conf import settings
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_snapshots_list_is_paginated(snapshots):
    client = APIClient()
    response = client.get('/api/snapshots/')
    assert response.status_code == 200
    assert response.data['count'] == 3
    assert response.data['next'] is not None
    assert len(response.data['results']) <= settings.REST_FRAMEWORK['PAGE_SIZE']


@pytest.mark.django_db
def test_coin_price_history(coins):
    client = APIClient()
    response = client.get('/api/coins/?symbol=C1')
    assert response.status_code == 200
    assert response.data['count'] == 2


def test_snapshots_list_uses_prefetch_related(coins, django_assert_num_queries):
    """N+1 guard: список снимков должен делать фиксированное число SQL-запросов
    независимо от количества снимков и связанных цен."""
    client = APIClient()
    with django_assert_num_queries(3):
        response = client.get('/api/snapshots/')
    assert response.status_code == 200
