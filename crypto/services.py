"""
Сервисный слой для работы с watchlist.
Содержит бизнес-логику: валидация символа через API биржи,
управление списком отслеживаемых монет пользователя.
Не зависит от DRF — работает только с Django ORM и стандартной библиотекой.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import (
    Avg,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    Min,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
)

from crypto.cache import (
    invalidate_portfolio,
    invalidate_watchlist,
)
from crypto.exceptions import (
    CoinNotInLatestSnapshotError,
    InsufficientFundsError,
    InvalidSellAmountError,
    PositionNotFoundError,
    SymbolNotFoundOnExchangeError,
    WatchlistDuplicateError,
)
from crypto.models import Balance, CoinPrice, Portfolio, Snapshot, WatchlistItem
from src.api_client import ApiClient


def _get_latest_snapshot_prices() -> QuerySet[CoinPrice]:
    """
    Queryset цен последнего снимка рынка. Если снимков ещё нет — возвращает
    гарантированно пустой queryset (CoinPrice.objects.none()), чтобы вызывающий
    код не различал «снимков нет» и «снимок есть, но пустой».
    """
    latest_snapshot = Snapshot.objects.order_by("-created_at").first()
    if latest_snapshot is None:
        return CoinPrice.objects.none()
    return CoinPrice.objects.filter(snapshot=latest_snapshot)


def get_market_stats() -> dict[str, float] | None:
    """
    Агрегированная статистика цен по последнему снимку рынка.
    Возвращает словарь с min/max/avg цены и суммой капитализации,
    либо None, если нет ни одного снимка или снимок пустой.
    """
    stats = _get_latest_snapshot_prices().aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
        avg_price=Avg("price"),
        total_market_cap=Sum("market_cap"),
    )

    if stats["min_price"] is None:
        return None

    return stats


def get_top_movers() -> dict[str, QuerySet[CoinPrice, CoinPrice]] | None:
    """
    Топ-5 растущих и топ-5 падающих монет по change_24h за последний снимок.
    Возвращает словарь с двумя querysets, либо None, если нет ни одного снимка
    или последний снимок пустой.
    """
    prices = _get_latest_snapshot_prices()
    if not prices.exists():
        return None

    return {
        "top_gainers": prices.order_by("-change_24h")[:5],
        "top_losers": prices.order_by("change_24h")[:5],
    }


def get_volume_leaders() -> dict[str, QuerySet[CoinPrice, CoinPrice]] | None:
    """
    Топ-10 монет по объёму торгов за последний снимок.
    Возвращает словарь с queryset, либо None, если нет ни одного снимка
    или последний снимок пустой.
    """
    prices = _get_latest_snapshot_prices()
    if not prices.exists():
        return None

    return {
        "leaders": prices.order_by("-volume")[:10],
    }


def get_user_watchlist(user: User) -> QuerySet[WatchlistItem, WatchlistItem]:
    """Возвращает все монеты из watchlist пользователя."""
    return WatchlistItem.objects.filter(user=user)


def remove_from_watchlist(user: User, symbol: str) -> bool:
    """
    Удаляет монету из watchlist.
    Возвращает True если удалена, False если не найдена.
    """
    deleted_count, _ = WatchlistItem.objects.filter(user=user, symbol=symbol).delete()
    if deleted_count:
        invalidate_watchlist(user.id)
    return bool(deleted_count)


def _validate_coingecko(symbol: str) -> tuple[str, str]:
    """Проверяет существование символа через CoinGecko API."""
    client = ApiClient(base_url=settings.COINGECKO_BASE_URL)
    data = client.get_json(endpoint="/search", params={"query": symbol})

    symbol_upper = symbol.upper()
    by_symbol = {c["symbol"]: c["name"] for c in data["coins"]}
    name = by_symbol.get(symbol_upper)
    if name is None:
        raise SymbolNotFoundOnExchangeError
    return symbol_upper, name


def _validate_cmc(symbol: str) -> tuple[str, str]:
    """Проверяет существование символа через CoinMarketCap API."""
    client = ApiClient(
        base_url=settings.CMC_BASE_URL,
        headers={"X-CMC_PRO_API_KEY": settings.CMC_API_KEY},
    )
    data = client.get_json(
        endpoint="/cryptocurrency/map",
        params={"symbol": symbol.upper()},
    )

    symbol_upper = symbol.upper()
    by_symbol = {c["symbol"]: c["name"] for c in data.get("data", [])}
    name = by_symbol.get(symbol_upper)
    if name is None:
        raise SymbolNotFoundOnExchangeError
    return symbol_upper, name


VALIDATORS = {
    "coingecko": _validate_coingecko,
    "coinmarketcap": _validate_cmc,
}


def validate_symbol(symbol: str) -> tuple[str, str]:
    """
    Проверяет существование символа через API выбранной биржи.
    Возвращает (symbol, name).
    """
    provider = settings.CRYPTO_PROVIDER
    validator = VALIDATORS.get(provider)

    if validator is None:
        raise ValueError(f"Неизвестный провайдер: {provider}")

    return validator(symbol)


def add_to_watchlist(user: User, symbol: str) -> WatchlistItem:
    """Валидирует символ и добавляет монету в watchlist пользователя."""
    coin_info = validate_symbol(symbol)

    try:
        item = WatchlistItem.objects.create(
            user=user,
            symbol=coin_info[0],
            coin_name=coin_info[1],
        )
    except IntegrityError:
        raise WatchlistDuplicateError

    invalidate_watchlist(user.id)
    return item


@transaction.atomic
def buy_coin(user: User, symbol: str, amount: Decimal) -> Portfolio:
    """
    Покупка монеты по цене последнего снимка. Атомарно: списание + создание позиции
    или ничего. Баланс блокируется на время транзакции для защиты от lost update
    при параллельных покупках.
    """
    symbol = symbol.upper()

    price = (
        _get_latest_snapshot_prices()
        .filter(symbol=symbol)
        .values_list("price", flat=True)
        .first()
    )
    if price is None:
        raise CoinNotInLatestSnapshotError

    balance = Balance.objects.select_for_update().get(user=user)
    cost = price * amount
    if balance.amount < cost:
        raise InsufficientFundsError

    balance.amount -= cost
    balance.save()

    position = Portfolio.objects.create(
        user=user,
        symbol=symbol,
        amount=amount,
        buy_price=price,
    )
    transaction.on_commit(lambda: invalidate_portfolio(user.id))
    return position


@transaction.atomic
def sell_position(user: User, position_id: int, amount: Decimal) -> dict:
    """
    Продажа части позиции по текущей цене (последний снимок). Атомарно:
    либо позиция уменьшается/удаляется + баланс пополняется, либо ничего.
    Блокируется и позиция, и баланс - защита от параллельных продаж той же
    позиции и от lost update на балансе.
    """
    try:
        position = Portfolio.objects.select_for_update().get(id=position_id, user=user)
    except Portfolio.DoesNotExist:
        raise PositionNotFoundError

    if amount > position.amount:
        raise InvalidSellAmountError

    price = (
        _get_latest_snapshot_prices()
        .filter(symbol=position.symbol)
        .values_list("price", flat=True)
        .first()
    )
    if price is None:
        raise CoinNotInLatestSnapshotError

    proceeds = price * amount
    balance = Balance.objects.select_for_update().get(user=user)
    balance.amount += proceeds
    balance.save()

    if amount == position.amount:
        position.delete()
        remaining_id = None
        remaining_amount = Decimal("0")
    else:
        position.amount -= amount
        position.save()
        remaining_id = position.id
        remaining_amount = position.amount

    transaction.on_commit(lambda: invalidate_portfolio(user.id))

    return {
        "position_id": remaining_id,
        "remaining_amount": remaining_amount,
        "sale_price": price,
        "proceeds": proceeds,
        "new_balance": balance.amount,
    }


def get_user_portfolio(user: User) -> dict:
    """
    Позиции пользователя с текущей ценой и P&L + суммарные показатели.
    Подсчёт через annotate + коррелированный Subquery -> один SQL,
    избегаем N+1 на цене из последнего снимка для каждой позиции.
    """
    latest_snapshot_id = Snapshot.objects.order_by("-created_at").values("id")[:1]

    current_price_sq = CoinPrice.objects.filter(
        snapshot=Subquery(latest_snapshot_id),
        symbol=OuterRef("symbol"),
    ).values("price")[:1]

    # output_field обязателен: иначе Django теряет точность Decimal на умножении.
    money = DecimalField(max_digits=22, decimal_places=2)
    positions = (
        Portfolio.objects.filter(user=user)
        .annotate(current_price=Subquery(current_price_sq))
        .annotate(
            current_value=ExpressionWrapper(
                F("current_price") * F("amount"), output_field=money
            ),
            pnl=ExpressionWrapper(
                (F("current_price") - F("buy_price")) * F("amount"),
                output_field=money,
            ),
        )
    )

    totals = positions.aggregate(
        total_value=Sum("current_value"),
        total_pnl=Sum("pnl"),
    )

    return {
        "positions": positions,
        "total_value": totals["total_value"] or Decimal("0"),
        "total_pnl": totals["total_pnl"] or Decimal("0"),
    }
