from django.conf import settings
from rest_framework.test import APIClient


def test_snapshots_list_is_paginated(snapshots):
    client = APIClient()
    response = client.get('/api/snapshots/')
    assert response.status_code == 200
    assert response.data['count'] == 3
    assert response.data['next'] is not None
    assert len(response.data['results']) <= settings.REST_FRAMEWORK['PAGE_SIZE']


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


def test_market_stats_returns_aggregates_for_latest_snapshot(analytics_snapshot):
    client = APIClient()
    response = client.get('/api/analytics/market-stats/')
    assert response.status_code == 200
    assert response.data['min_price'] == '10.000000'
    assert response.data['max_price'] == '100.000000'
    assert response.data['avg_price'] == '55.00000000'
    assert response.data['total_market_cap'] == '5500000.00'


def test_market_stats_returns_404_when_latest_snapshot_is_empty(snapshots):
    """snapshots фикстура создаёт 3 снимка без цен — последний пустой."""
    client = APIClient()
    response = client.get('/api/analytics/market-stats/')
    assert response.status_code == 404


def test_market_stats_returns_404_when_no_snapshots(db):
    client = APIClient()
    response = client.get('/api/analytics/market-stats/')
    assert response.status_code == 404
