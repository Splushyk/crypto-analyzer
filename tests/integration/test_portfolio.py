"""
Интеграционные тесты портфеля и баланса пользователя.
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from crypto.exceptions import (
    CoinNotInLatestSnapshotError,
    InsufficientFundsError,
    InvalidSellAmountError,
    PositionNotFoundError,
)
from crypto.models import Balance, CoinPrice, Portfolio, Snapshot
from crypto.services import buy_coin, sell_position


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


@pytest.fixture
def btc_position(funded_user, latest_snapshot_with_btc):
    """Покупка 5 BTC по 100$. После: баланс 500, позиция 5 BTC."""
    return buy_coin(funded_user, "BTC", Decimal("5"))


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


def test_sell_position_partial(funded_user, btc_position):
    """Продали часть: позиция уменьшилась, баланс пополнился."""
    result = sell_position(funded_user, btc_position.id, Decimal("2"))

    funded_user.balance.refresh_from_db()
    btc_position.refresh_from_db()
    assert btc_position.amount == Decimal("3")
    # Баланс после buy = 500, продажа 2 BTC по 100 (+200) -> 700
    assert funded_user.balance.amount == Decimal("700")
    assert result["position_id"] == btc_position.id
    assert result["remaining_amount"] == Decimal("3")
    assert result["proceeds"] == Decimal("200")


def test_sell_position_full_deletes_it(funded_user, btc_position):
    """Продали всё - позиция удалена."""
    result = sell_position(funded_user, btc_position.id, Decimal("5"))

    funded_user.balance.refresh_from_db()
    assert not Portfolio.objects.filter(id=btc_position.id).exists()
    # Баланс после buy = 500, продажа 5 BTC по 100 (+500) -> 1000
    assert funded_user.balance.amount == Decimal("1000")
    assert result["position_id"] is None
    assert result["remaining_amount"] == Decimal("0")


def test_sell_position_rolls_back_when_amount_too_high(funded_user, btc_position):
    """Продажа сверх остатка - откат, ничего не меняется."""
    funded_user.balance.refresh_from_db()
    initial_balance = funded_user.balance.amount

    with pytest.raises(InvalidSellAmountError):
        sell_position(funded_user, btc_position.id, Decimal("10"))

    funded_user.balance.refresh_from_db()
    btc_position.refresh_from_db()
    assert funded_user.balance.amount == initial_balance
    assert btc_position.amount == Decimal("5")


def test_sell_position_fails_for_unknown_id(funded_user, latest_snapshot_with_btc):
    """Несуществующая позиция - 404."""
    initial_balance = funded_user.balance.amount

    with pytest.raises(PositionNotFoundError):
        sell_position(funded_user, position_id=99999, amount=Decimal("1"))

    funded_user.balance.refresh_from_db()
    assert funded_user.balance.amount == initial_balance


def test_sell_position_fails_for_other_users_position(
    user_b, btc_position, latest_snapshot_with_btc
):
    """Чужая позиция не находится - 404, у владельца ничего не изменилось."""
    with pytest.raises(PositionNotFoundError):
        sell_position(user_b, btc_position.id, Decimal("1"))

    btc_position.refresh_from_db()
    assert btc_position.amount == Decimal("5")


def test_sell_position_rolls_back_when_coin_not_in_latest_snapshot(
    funded_user, btc_position
):
    """Свежий снимок без BTC - продать нельзя, баланс и позиция нетронуты."""
    funded_user.balance.refresh_from_db()
    initial_balance = funded_user.balance.amount
    # Создаём более свежий снимок без BTC.
    Snapshot.objects.create(total_market_cap=Decimal("0"))

    with pytest.raises(CoinNotInLatestSnapshotError):
        sell_position(funded_user, btc_position.id, Decimal("1"))

    funded_user.balance.refresh_from_db()
    btc_position.refresh_from_db()
    assert funded_user.balance.amount == initial_balance
    assert btc_position.amount == Decimal("5")
