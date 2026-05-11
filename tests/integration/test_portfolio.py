"""
Интеграционные тесты портфеля и баланса пользователя.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from crypto.cache import portfolio_cache_key
from crypto.exceptions import (
    CoinNotInLatestSnapshotError,
    InsufficientFundsError,
    InvalidSellAmountError,
    PositionNotFoundError,
)
from crypto.models import Balance, CoinPrice, Portfolio, Snapshot
from crypto.services import (
    buy_coin,
    get_portfolio_history,
    get_user_portfolio,
    sell_position,
)


@pytest.fixture
def make_btc_snapshot(db):
    """Фабрика снимков с BTC по заданной цене (опционально с явным created_at)."""

    def _make(price, created_at=None):
        price = Decimal(price)
        snapshot = Snapshot.objects.create(total_market_cap=price)
        if created_at is not None:
            Snapshot.objects.filter(pk=snapshot.pk).update(created_at=created_at)
            snapshot.refresh_from_db()
        CoinPrice.objects.create(
            snapshot=snapshot,
            name="Bitcoin",
            symbol="BTC",
            price=price,
            change_24h=0,
            volume=Decimal("0"),
            market_cap=price,
        )
        return snapshot

    return _make


@pytest.fixture
def make_empty_snapshot(db):
    """Фабрика пустых снимков без CoinPrice для проверок типа
    "монеты нет в последнем снимке".
    """

    def _make():
        return Snapshot.objects.create(total_market_cap=Decimal("0"))

    return _make


@pytest.fixture
def latest_snapshot_with_btc(make_btc_snapshot):
    """Снимок с одной монетой BTC по цене 100$."""
    return make_btc_snapshot("100")


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


def assert_balance(user, expected):
    """Перечитывает баланс из БД и сверяет с ожидаемым."""
    user.balance.refresh_from_db()
    assert user.balance.amount == expected


def test_balance_is_created_for_new_user(db):
    """При создании юзера сигналом автоматически заводится нулевой баланс."""
    user = User.objects.create_user(username="new_user", password="pass12345")

    assert Balance.objects.filter(user=user).count() == 1
    assert user.balance.amount == Decimal("0")


def test_balance_is_not_recreated_on_user_update(user_a):
    """
    При сохранении уже существующего юзера сигнал не создаёт новый Balance
    и не сбрасывает amount: тот же объект, та же сумма.
    """
    user_a.balance.amount = Decimal("777")
    user_a.balance.save()
    initial_pk = user_a.balance.pk

    user_a.email = "changed@example.com"
    user_a.save()

    assert Balance.objects.filter(user=user_a).count() == 1
    user_a.balance.refresh_from_db()
    assert user_a.balance.pk == initial_pk
    assert user_a.balance.amount == Decimal("777")


def test_buy_coin_success(funded_user, latest_snapshot_with_btc):
    """Успешная покупка: баланс уменьшается, позиция создаётся."""
    position = buy_coin(funded_user, "BTC", Decimal("2"))

    assert_balance(funded_user, Decimal("800"))  # 1000 - 100*2
    assert Portfolio.objects.filter(user=funded_user).count() == 1
    assert position.symbol == "BTC"
    assert position.amount == Decimal("2")
    assert position.buy_price == Decimal("100")


@pytest.mark.parametrize(
    "symbol, amount, expected_exc",
    [
        ("BTC", Decimal("100"), InsufficientFundsError),  # 100*100 > 1000
        ("ETH", Decimal("1"), CoinNotInLatestSnapshotError),
    ],
    ids=["insufficient_funds", "coin_not_in_snapshot"],
)
def test_buy_coin_rolls_back_on_failure(
    funded_user, latest_snapshot_with_btc, symbol, amount, expected_exc
):
    """При любой ошибке buy_coin — баланс не тронут, позиция не создана."""
    initial_balance = funded_user.balance.amount

    with pytest.raises(expected_exc):
        buy_coin(funded_user, symbol, amount)

    assert_balance(funded_user, initial_balance)
    assert Portfolio.objects.filter(user=funded_user).count() == 0


def test_sell_position_partial_decreases_amount_and_credits_balance(
    funded_user, btc_position
):
    """Продали часть: позиция уменьшилась, баланс пополнился."""
    result = sell_position(funded_user, btc_position.id, Decimal("2"))

    btc_position.refresh_from_db()
    assert btc_position.amount == Decimal("3")
    # Баланс после buy = 500, продажа 2 BTC по 100 (+200) -> 700
    assert_balance(funded_user, Decimal("700"))
    assert result["position_id"] == btc_position.id
    assert result["remaining_amount"] == Decimal("3")
    assert result["proceeds"] == Decimal("200")


def test_sell_position_full_amount_deletes_position(funded_user, btc_position):
    """Продали весь объём — позиция удалена."""
    result = sell_position(funded_user, btc_position.id, Decimal("5"))

    assert not Portfolio.objects.filter(id=btc_position.id).exists()
    # Баланс после buy = 500, продажа 5 BTC по 100 (+500) -> 1000
    assert_balance(funded_user, Decimal("1000"))
    assert result["position_id"] is None
    assert result["remaining_amount"] == Decimal("0")


def test_sell_position_rolls_back_when_amount_too_high(funded_user, btc_position):
    """Продажа сверх остатка — откат, ничего не меняется."""
    funded_user.balance.refresh_from_db()
    initial_balance = funded_user.balance.amount

    with pytest.raises(InvalidSellAmountError):
        sell_position(funded_user, btc_position.id, Decimal("10"))

    btc_position.refresh_from_db()
    assert_balance(funded_user, initial_balance)
    assert btc_position.amount == Decimal("5")


def test_sell_position_fails_for_unknown_id(funded_user, latest_snapshot_with_btc):
    """Несуществующая позиция — 404."""
    initial_balance = funded_user.balance.amount

    with pytest.raises(PositionNotFoundError):
        sell_position(funded_user, position_id=99999, amount=Decimal("1"))

    assert_balance(funded_user, initial_balance)


def test_sell_position_fails_for_other_users_position(user_b, btc_position):
    """Чужая позиция не находится (IDOR) — 404, у владельца ничего не изменилось."""
    with pytest.raises(PositionNotFoundError):
        sell_position(user_b, btc_position.id, Decimal("1"))

    btc_position.refresh_from_db()
    assert btc_position.amount == Decimal("5")


def test_sell_position_rolls_back_when_coin_not_in_latest_snapshot(
    funded_user, btc_position, make_empty_snapshot
):
    """Свежий снимок без BTC — продать нельзя, баланс и позиция нетронуты."""
    funded_user.balance.refresh_from_db()
    initial_balance = funded_user.balance.amount
    make_empty_snapshot()

    with pytest.raises(CoinNotInLatestSnapshotError):
        sell_position(funded_user, btc_position.id, Decimal("1"))

    btc_position.refresh_from_db()
    assert_balance(funded_user, initial_balance)
    assert btc_position.amount == Decimal("5")


def test_get_user_portfolio_calculates_metrics(
    funded_user, latest_snapshot_with_btc, make_btc_snapshot
):
    """
    P&L: купили 2 BTC по 100, цена выросла до 150 (новый снимок) - P&L = +100.
    Считается на стороне БД через annotate+Subquery.
    """
    buy_coin(funded_user, "BTC", Decimal("2"))
    make_btc_snapshot("150")

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
    funded_user, latest_snapshot_with_btc, make_empty_snapshot
):
    """
    Монета купленной позиции отсутствует в последнем снимке:
    current_price/value/pnl должны быть None, total_value/pnl не падают.
    """
    buy_coin(funded_user, "BTC", Decimal("1"))
    make_empty_snapshot()

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


def test_portfolio_history_tracks_value_across_snapshots(
    funded_user, latest_snapshot_with_btc, make_btc_snapshot
):
    """
    Купили 2 BTC, после этого появилось ещё 2 снимка с разными ценами.
    История должна вернуть две точки с пересчитанной стоимостью
    (фикстурный снимок ДО покупки не учитывается).
    """
    buy_coin(funded_user, "BTC", Decimal("2"))
    now = timezone.now()
    make_btc_snapshot("100", created_at=now + timedelta(hours=1))
    make_btc_snapshot("150", created_at=now + timedelta(hours=2))

    history = get_portfolio_history(funded_user)

    assert len(history) == 2
    # сортировка по created_at — гарантирована явными timestamp'ами
    assert history[0]["portfolio_value"] == Decimal("200")  # 100 * 2
    assert history[1]["portfolio_value"] == Decimal("300")  # 150 * 2


def test_portfolio_history_excludes_snapshots_before_purchase(
    funded_user, latest_snapshot_with_btc, make_btc_snapshot
):
    """
    Снимки, сделанные ДО покупки, не попадают в историю.
    Снимок-фикстура был до buy_coin, поэтому не учитывается.
    """
    buy_coin(funded_user, "BTC", Decimal("1"))
    new_snap = make_btc_snapshot("120")

    history = get_portfolio_history(funded_user)

    assert len(history) == 1
    assert history[0]["snapshot_id"] == new_snap.id
    assert history[0]["portfolio_value"] == Decimal("120")


# --- HTTP-уровень ---


def test_buy_endpoint_returns_201_with_position(
    auth_client_a, funded_user, latest_snapshot_with_btc
):
    """POST /portfolio/buy/ - happy-path: 201 с данными созданной позиции."""
    response = auth_client_a.post(
        "/api/v1/portfolio/buy/",
        {"symbol": "BTC", "amount": "0.5"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["symbol"] == "BTC"
    assert Decimal(response.data["amount"]) == Decimal("0.5")
    assert Decimal(response.data["buy_price"]) == Decimal("100")


@pytest.mark.parametrize(
    "method, url",
    [
        ("get", "/api/v1/portfolio/"),
        ("get", "/api/v1/portfolio/history/"),
        ("post", "/api/v1/portfolio/buy/"),
        ("post", "/api/v1/portfolio/positions/1/sell/"),
    ],
)
def test_portfolio_endpoints_require_auth(method, url):
    """Без токена все portfolio-эндпоинты отвечают 401."""
    client = APIClient()
    response = getattr(client, method)(url, {}, format="json")
    assert response.status_code == 401


def test_sell_endpoint_rejects_other_users_position(auth_client_b, btc_position):
    """IDOR: другой залогиненный юзер не может продать чужую позицию (404)."""
    response = auth_client_b.post(
        f"/api/v1/portfolio/positions/{btc_position.id}/sell/",
        {"amount": "1"},
        format="json",
    )

    assert response.status_code == 404


# --- Cache invalidation ---


@pytest.mark.django_db(transaction=True)
def test_buy_coin_invalidates_portfolio_cache(funded_user, latest_snapshot_with_btc):
    """После успешного buy_coin кеш портфеля должен быть очищен."""
    key = portfolio_cache_key(funded_user.id)
    cache.set(key, "old-data")

    buy_coin(funded_user, "BTC", Decimal("1"))

    assert cache.get(key) is None
