"""
Интеграционные тесты портфеля и баланса пользователя.
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from crypto.exceptions import (
    CoinNotInLatestSnapshotError,
    InsufficientFundsError,
)
from crypto.models import Balance, CoinPrice, Portfolio, Snapshot
from crypto.services import buy_coin


@pytest.fixture
def latest_snapshot_with_btc(db):
    """Снимок с одной монетой BTC по цене 100$."""
    snapshot = Snapshot.objects.create(total_market_cap=Decimal("100"))
    CoinPrice.objects.create(
        snapshot=snapshot,
        name="Bitcoin",
        symbol="BTC",
        price=Decimal("100"),
        change_24h=0,
        volume=Decimal("0"),
        market_cap=Decimal("100"),
    )
    return snapshot


@pytest.fixture
def funded_user(user_a):
    """Пользователь с балансом 1000$."""
    user_a.balance.amount = Decimal("1000")
    user_a.balance.save()
    return user_a


def test_balance_is_created_for_new_user(db):
    """При создании юзера сигналом автоматически заводится нулевой баланс."""
    user = User.objects.create_user(username="new_user", password="pass12345")

    assert Balance.objects.filter(user=user).count() == 1
    assert user.balance.amount == Decimal("0")


def test_balance_is_not_recreated_on_user_update(user_a):
    """При сохранении уже существующего юзера новый Balance не создаётся."""
    initial_count = Balance.objects.filter(user=user_a).count()

    user_a.email = "changed@example.com"
    user_a.save()

    assert Balance.objects.filter(user=user_a).count() == initial_count


def test_buy_coin_success(funded_user, latest_snapshot_with_btc):
    """Успешная покупка: баланс уменьшается, позиция создаётся."""
    position = buy_coin(funded_user, "BTC", Decimal("2"))

    funded_user.balance.refresh_from_db()
    assert funded_user.balance.amount == Decimal("800")  # 1000 - 100*2
    assert Portfolio.objects.filter(user=funded_user).count() == 1
    assert position.symbol == "BTC"
    assert position.amount == Decimal("2")
    assert position.buy_price == Decimal("100")


def test_buy_coin_rolls_back_on_insufficient_funds(
    funded_user, latest_snapshot_with_btc
):
    """Не хватает баланса -> откат: баланс не тронут, позиция не создана."""
    initial_balance = funded_user.balance.amount

    with pytest.raises(InsufficientFundsError):
        buy_coin(funded_user, "BTC", Decimal("100"))  # 100*100 = 10000 > 1000

    funded_user.balance.refresh_from_db()
    assert funded_user.balance.amount == initial_balance
    assert Portfolio.objects.filter(user=funded_user).count() == 0


def test_buy_coin_fails_when_symbol_not_in_latest_snapshot(
    funded_user, latest_snapshot_with_btc
):
    """Монеты нет в последнем снимке -> ошибка, баланс не тронут."""
    initial_balance = funded_user.balance.amount

    with pytest.raises(CoinNotInLatestSnapshotError):
        buy_coin(funded_user, "ETH", Decimal("1"))

    funded_user.balance.refresh_from_db()
    assert funded_user.balance.amount == initial_balance
    assert Portfolio.objects.filter(user=funded_user).count() == 0
