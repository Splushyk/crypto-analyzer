import pytest

from rest_framework.test import APIClient

from crypto.models import Snapshot, CoinPrice


@pytest.fixture
def snapshots(db):
    snap_1 = Snapshot.objects.create(total_market_cap=1000)
    snap_2 = Snapshot.objects.create(total_market_cap=2000)
    snap_3 = Snapshot.objects.create(total_market_cap=3000)
    return snap_1, snap_2, snap_3


@pytest.fixture
def analytics_snapshot(db):
    """Создаёт один снимок рынка с 10 монетами с известными значениями
    для проверки аналитических эндпоинтов.

    Значения подобраны так, чтобы легко проверялись агрегаты и сортировки:
    - price:       10, 20, 30, ..., 100 (min=10, max=100, avg=55)
    - change_24h:  +9, +7, +5, +3, +1, -1, -3, -5, -7, -9
    - volume:      1000, 2000, ..., 10000
    - market_cap:  100000, 200000, ..., 1000000 (sum=5500000)
    """
    snapshot = Snapshot.objects.create(total_market_cap=5500000)
    for i in range(1, 11):
        CoinPrice.objects.create(
            snapshot=snapshot,
            name=f"Coin{i}",
            symbol=f"C{i}",
            price=i * 10,
            change_24h=11 - 2 * i,
            volume=i * 1000,
            market_cap=i * 100000,
        )
    return snapshot


@pytest.fixture
def coins(snapshots):
    snap_1, snap_2, snap_3 = snapshots
    c1_snap1 = CoinPrice.objects.create(
        snapshot=snap_1,
        name="Coin One",
        symbol="C1",
        price=100,
        change_24h=1.5,
        volume=1000,
        market_cap=10000,
    )
    c1_snap2 = CoinPrice.objects.create(
        snapshot=snap_2,
        name="Coin One",
        symbol="C1",
        price=110,
        change_24h=2.0,
        volume=1100,
        market_cap=11000,
    )
    c2_snap1 = CoinPrice.objects.create(
        snapshot=snap_1,
        name="Coin Two",
        symbol="C2",
        price=200,
        change_24h=-3.0,
        volume=2000,
        market_cap=20000,
    )
    return c1_snap1, c1_snap2, c2_snap1


@pytest.fixture
def auth_client_a(user_a):
    """APIClient, аутентифицированный как user_a через JWT."""
    client = APIClient()
    response = client.post('/api/token/', {
        'username': 'name_a',
        'password': 'password123',
    })
    token = response.data['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


@pytest.fixture
def auth_client_b(user_b):
    """APIClient, аутентифицированный как user_b через JWT."""
    client = APIClient()
    response = client.post('/api/token/', {
        'username': 'name_b',
        'password': 'password456',
    })
    token = response.data['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client
