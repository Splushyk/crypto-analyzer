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
from crypto.services import buy_coin, get_user_portfolio, sell_position


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


def test_get_user_portfolio_calculates_metrics(funded_user, latest_snapshot_with_btc):
    """
    P&L: купили 2 BTC по 100, цена выросла до 150 (новый снимок) - P&L = +100.
    Считается на стороне БД через annotate+Subquery.
    """
    buy_coin(funded_user, "BTC", Decimal("2"))
    # Новый снимок с другой ценой — фиксируем «рост» BTC.
    new_snap = Snapshot.objects.create(total_market_cap=Decimal("150"))
    CoinPrice.objects.create(
        snapshot=new_snap,
        name="Bitcoin",
        symbol="BTC",
        price=Decimal("150"),
        change_24h=0,
        volume=Decimal("0"),
        market_cap=Decimal("150"),
    )

    result = get_user_portfolio(funded_user)
    positions = list(result["positions"])

    assert len(positions) == 1
    pos = positions[0]
    assert pos.symbol == "BTC"
    assert pos.amount == Decimal("2")
    assert pos.buy_price == Decimal("100")
    assert pos.current_price == Decimal("150")
    assert pos.current_value == Decimal("300")  # 150 * 2
    assert pos.pnl == Decimal("100")  # (150 - 100) * 2

    assert result["total_value"] == Decimal("300")
    assert result["total_pnl"] == Decimal("100")


def test_get_user_portfolio_handles_missing_coin_in_latest_snapshot(
    funded_user, latest_snapshot_with_btc
):
    """
    Монета купленной позиции отсутствует в последнем снимке:
    current_price/value/pnl должны быть None, total_value/pnl не падают.
    """
    buy_coin(funded_user, "BTC", Decimal("1"))
    # Свежий снимок БЕЗ BTC.
    Snapshot.objects.create(total_market_cap=Decimal("0"))

    result = get_user_portfolio(funded_user)
    pos = list(result["positions"])[0]

    assert pos.current_price is None
    assert pos.current_value is None
    assert pos.pnl is None
    assert result["total_value"] == Decimal("0")
    assert result["total_pnl"] == Decimal("0")


def test_get_user_portfolio_isolates_users(
    funded_user, user_b, latest_snapshot_with_btc
):
    """Юзер видит только свои позиции."""
    buy_coin(funded_user, "BTC", Decimal("1"))
    user_b.balance.amount = Decimal("1000")
    user_b.balance.save()
    buy_coin(user_b, "BTC", Decimal("3"))

    result_a = get_user_portfolio(funded_user)
    result_b = get_user_portfolio(user_b)

    assert len(list(result_a["positions"])) == 1
    assert len(list(result_b["positions"])) == 1
    assert list(result_a["positions"])[0].amount == Decimal("1")
    assert list(result_b["positions"])[0].amount == Decimal("3")
