import pytest

from crypto.models import Snapshot, CoinPrice

pytestmark = pytest.mark.integration


@pytest.fixture
def snapshots(db):
    snap_1 = Snapshot.objects.create(total_market_cap=1000)
    snap_2 = Snapshot.objects.create(total_market_cap=2000)
    snap_3 = Snapshot.objects.create(total_market_cap=3000)
    return snap_1, snap_2, snap_3


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
