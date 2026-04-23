"""
Интеграционные тесты REST API: snapshots, coins, аналитика.
Тестируется полный HTTP-цикл: запрос -> view -> сервис -> БД -> ответ.
"""

from typing import cast

import pytest
from django.conf import settings
from rest_framework.test import APIClient

# Тесты snapshots


def test_snapshots_list_is_paginated(snapshots):
    client = APIClient()
    response = client.get("/api/snapshots/")
    assert response.status_code == 200
    assert response.data["count"] == 3
    assert response.data["next"] is not None
    page_size = cast(int, settings.REST_FRAMEWORK["PAGE_SIZE"])
    assert len(response.data["results"]) <= page_size


def test_snapshots_list_uses_prefetch_related(coins, django_assert_num_queries):
    """N+1 guard: список снимков должен делать фиксированное число SQL-запросов
    независимо от количества снимков и связанных цен."""
    client = APIClient()
    with django_assert_num_queries(3):
        response = client.get("/api/snapshots/")
    assert response.status_code == 200


# Тесты coin price history + filter


def test_coin_price_history(coins):
    client = APIClient()
    response = client.get("/api/coins/?symbol=C1")
    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.parametrize(
    "query, expected_symbols",
    [
        ("min_price=50", {"C5", "C6", "C7", "C8", "C9", "C10"}),
        ("max_price=30", {"C1", "C2", "C3"}),
        ("min_price=30&max_price=70", {"C3", "C4", "C5", "C6", "C7"}),
        ("symbol=C5&min_price=1", {"C5"}),
    ],
    ids=[
        "min_price_only",
        "max_price_only",
        "price_range",
        "symbol_and_min_price",
    ],
)
def test_coins_filter(analytics_snapshot, query, expected_symbols):
    client = APIClient()
    response = client.get(f"/api/coins/?{query}")
    assert response.status_code == 200
    assert response.data["count"] == len(expected_symbols)
    symbols = {c["symbol"] for c in response.data["results"]}
    assert symbols == expected_symbols


def test_coins_filter_returns_400_on_invalid_min_price(analytics_snapshot):
    """Нечисловое значение min_price -> 400 от сериализатора-валидатора."""
    client = APIClient()
    response = client.get("/api/coins/?min_price=abc")
    assert response.status_code == 400


# Тесты market-stats


def test_market_stats_returns_aggregates_for_latest_snapshot(analytics_snapshot):
    client = APIClient()
    response = client.get("/api/analytics/market-stats/")
    assert response.status_code == 200
    assert response.data["min_price"] == "10.000000"
    assert response.data["max_price"] == "100.000000"
    assert response.data["avg_price"] == "55.00000000"
    assert response.data["total_market_cap"] == "5500000.00"


def test_market_stats_returns_404_when_latest_snapshot_is_empty(snapshots):
    """snapshots фикстура создаёт 3 снимка без цен — последний пустой."""
    client = APIClient()
    response = client.get("/api/analytics/market-stats/")
    assert response.status_code == 404


def test_market_stats_returns_404_when_no_snapshots(db):
    client = APIClient()
    response = client.get("/api/analytics/market-stats/")
    assert response.status_code == 404


# Тесты top-movers


def test_top_movers_returns_sorted_gainers_and_losers(analytics_snapshot):
    client = APIClient()
    response = client.get("/api/analytics/top-movers/")
    assert response.status_code == 200

    gainers = response.data["top_gainers"]
    losers = response.data["top_losers"]
    assert len(gainers) == 5
    assert len(losers) == 5

    # change_24h: +9, +7, +5, +3, +1, -1, -3, -5, -7, -9 (C1...C10)
    assert [c["symbol"] for c in gainers] == ["C1", "C2", "C3", "C4", "C5"]
    assert [c["symbol"] for c in losers] == ["C10", "C9", "C8", "C7", "C6"]


def test_top_movers_returns_404_when_latest_snapshot_is_empty(snapshots):
    client = APIClient()
    response = client.get("/api/analytics/top-movers/")
    assert response.status_code == 404


def test_top_movers_has_no_n_plus_one(analytics_snapshot, django_assert_num_queries):
    """N+1 guard: запросов должно быть фиксированное количество независимо
    от количества монет в снимке."""
    client = APIClient()
    with django_assert_num_queries(4):
        response = client.get("/api/analytics/top-movers/")
    assert response.status_code == 200


# Тесты volume-leaders


def test_volume_leaders_returns_coins_desc_sorted(analytics_snapshot):
    client = APIClient()
    response = client.get("/api/analytics/volume-leaders/")
    assert response.status_code == 200

    leaders = response.data["leaders"]
    assert len(leaders) == 10

    # volume: 1000, 2000, ..., 10000 (C1...C10)
    assert [c["symbol"] for c in leaders] == [
        "C10",
        "C9",
        "C8",
        "C7",
        "C6",
        "C5",
        "C4",
        "C3",
        "C2",
        "C1",
    ]


def test_volume_leaders_returns_404_when_latest_snapshot_is_empty(snapshots):
    client = APIClient()
    response = client.get("/api/analytics/volume-leaders/")
    assert response.status_code == 404


def test_volume_leaders_has_no_n_plus_one(
    analytics_snapshot, django_assert_num_queries
):
    """N+1 guard: запросов должно быть фиксированное количество независимо
    от количества монет в снимке."""
    client = APIClient()
    with django_assert_num_queries(3):
        response = client.get("/api/analytics/volume-leaders/")
    assert response.status_code == 200
