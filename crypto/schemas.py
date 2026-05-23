"""OpenAPI-схемы для эндпоинтов crypto. Каждый объект - готовый @extend_schema(...)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

from crypto.serializers import (
    AddToWatchlistSerializer,
    BuyCoinSerializer,
    CoinPriceSerializer,
    FetchSnapshotSerializer,
    MarketStatsSerializer,
    PortfolioHistoryEntrySerializer,
    PortfolioSerializer,
    SellPositionSerializer,
    SellResultSerializer,
    SnapshotSerializer,
    TopMoversSerializer,
    UserPortfolioSerializer,
    VolumeLeadersSerializer,
    WatchlistSerializer,
)

error_response = inline_serializer(
    name="ErrorResponse",
    fields={
        "error": serializers.CharField(),
        "code": serializers.CharField(),
    },
)


task_accepted_response = inline_serializer(
    name="TaskAcceptedResponse",
    fields={"task_id": serializers.CharField()},
)


# --- Coins ---


coin_history_schema = extend_schema(
    summary="История цен монет",
    description=(
        "Возвращает плоский список записей цен (по всем снимкам), отсортированный "
        "от свежих к старым. Поддерживает фильтрацию по символу и диапазону цены."
    ),
    responses={
        200: CoinPriceSerializer(many=True),
        400: OpenApiResponse(description="Некорректные значения фильтров"),
    },
    tags=["coins"],
)


# --- Watchlist ---


watchlist_get_schema = extend_schema(
    summary="Список отслеживаемых монет",
    description="Возвращает watchlist текущего пользователя.",
    responses={
        200: WatchlistSerializer(many=True),
        401: OpenApiResponse(description="Требуется аутентификация"),
    },
    tags=["watchlist"],
)


watchlist_post_schema = extend_schema(
    summary="Добавить монету в watchlist",
    description=(
        "Добавляет монету в watchlist текущего пользователя. "
        "Символ предварительно проверяется через провайдера биржи."
    ),
    request=AddToWatchlistSerializer,
    responses={
        201: WatchlistSerializer,
        400: OpenApiResponse(
            response=error_response,
            description="Символ не найден на бирже",
            examples=[
                OpenApiExample(
                    "Неизвестный тикер",
                    value={
                        "error": "Symbol not found on exchange.",
                        "code": "symbol_not_found",
                    },
                    status_codes=["400"],
                ),
            ],
        ),
        401: OpenApiResponse(description="Требуется аутентификация"),
        409: OpenApiResponse(
            response=error_response,
            description="Монета уже в watchlist пользователя",
            examples=[
                OpenApiExample(
                    "Дубликат",
                    value={
                        "error": "Coin already in your watchlist.",
                        "code": "watchlist_duplicate",
                    },
                    status_codes=["409"],
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Добавить BTC",
            value={"symbol": "BTC"},
            request_only=True,
        ),
    ],
    tags=["watchlist"],
)


watchlist_delete_schema = extend_schema(
    summary="Удалить монету из watchlist",
    parameters=[
        OpenApiParameter(
            name="symbol",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Тикер монеты, которую требуется удалить.",
            examples=[OpenApiExample("BTC", value="BTC")],
        ),
    ],
    responses={
        204: OpenApiResponse(description="Удалено"),
        401: OpenApiResponse(description="Требуется аутентификация"),
        404: OpenApiResponse(
            response=error_response,
            description="Монета не найдена в watchlist пользователя",
            examples=[
                OpenApiExample(
                    "Не найдено",
                    value={
                        "error": "Coin is not in your watchlist.",
                        "code": "watchlist_item_not_found",
                    },
                    status_codes=["404"],
                ),
            ],
        ),
    },
    tags=["watchlist"],
)


# --- Portfolio ---


buy_coin_schema = extend_schema(
    summary="Купить монету",
    description=(
        "Покупает монету по цене последнего снимка рынка. Списывает стоимость "
        "с баланса пользователя и создаёт новую позицию в портфеле. Операция "
        "атомарна: при ошибке (нехватка средств, монеты нет в снимке) "
        "состояние БД не меняется."
    ),
    request=BuyCoinSerializer,
    responses={
        201: PortfolioSerializer,
        400: OpenApiResponse(
            response=error_response,
            description="Монеты нет в снимке или недостаточно средств",
            examples=[
                OpenApiExample(
                    "Монеты нет в снимке",
                    value={
                        "error": "Coin not present in the latest market snapshot.",
                        "code": "coin_not_in_snapshot",
                    },
                    status_codes=["400"],
                ),
                OpenApiExample(
                    "Недостаточно средств",
                    value={
                        "error": "Insufficient balance for this purchase.",
                        "code": "insufficient_funds",
                    },
                    status_codes=["400"],
                ),
            ],
        ),
        401: OpenApiResponse(description="Требуется аутентификация"),
    },
    examples=[
        OpenApiExample(
            "Купить 0.5 BTC",
            value={"symbol": "BTC", "amount": "0.5"},
            request_only=True,
        ),
    ],
    tags=["portfolio"],
)


portfolio_history_schema = extend_schema(
    summary="Динамика стоимости портфеля по снимкам",
    description=(
        "Возвращает стоимость портфеля текущего пользователя на момент "
        "каждого снимка рынка, начиная с самой ранней покупки. В каждый "
        "снимок учитываются только позиции, купленные до его даты. "
        "Если позиции не было в портфеле или её монеты не было в снимке - "
        "она вкладывает 0."
    ),
    responses={
        200: PortfolioHistoryEntrySerializer(many=True),
        401: OpenApiResponse(description="Требуется аутентификация"),
    },
    tags=["portfolio"],
)


portfolio_schema = extend_schema(
    summary="Портфель пользователя с P&L",
    description=(
        "Возвращает все позиции текущего пользователя с текущей ценой "
        "(из последнего снимка) и P&L по каждой позиции, плюс суммарную "
        "стоимость и суммарный P&L. Результат кешируется. Если монеты "
        "позиции нет в последнем снимке — current_price/value/pnl будут null."
    ),
    responses={
        200: UserPortfolioSerializer,
        401: OpenApiResponse(description="Требуется аутентификация"),
    },
    tags=["portfolio"],
)


sell_position_schema = extend_schema(
    summary="Продать монеты из позиции",
    description=(
        "Продаёт указанное количество монет из конкретной позиции портфеля "
        "по текущей цене последнего снимка. Если продаётся весь объём — "
        "позиция удаляется, иначе уменьшается. Выручка зачисляется на "
        "баланс. Операция атомарна: при ошибке (нет позиции, чужая позиция, "
        "объём больше остатка, монеты нет в снимке) состояние БД не меняется."
    ),
    request=SellPositionSerializer,
    parameters=[
        OpenApiParameter(
            name="position_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="ID позиции в портфеле.",
        ),
    ],
    responses={
        200: SellResultSerializer,
        400: OpenApiResponse(
            response=error_response,
            description="Объём больше остатка или монеты нет в снимке",
            examples=[
                OpenApiExample(
                    "Объём больше остатка",
                    value={
                        "error": "Cannot sell more than the position holds.",
                        "code": "invalid_sell_amount",
                    },
                    status_codes=["400"],
                ),
                OpenApiExample(
                    "Монеты нет в снимке",
                    value={
                        "error": "Coin not present in the latest market snapshot.",
                        "code": "coin_not_in_snapshot",
                    },
                    status_codes=["400"],
                ),
            ],
        ),
        401: OpenApiResponse(description="Требуется аутентификация"),
        404: OpenApiResponse(
            response=error_response,
            description="Позиция не найдена или принадлежит другому пользователю",
            examples=[
                OpenApiExample(
                    "Не найдено",
                    value={
                        "error": "Portfolio position not found.",
                        "code": "position_not_found",
                    },
                    status_codes=["404"],
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Продать 0.005 BTC из позиции",
            value={"amount": "0.005"},
            request_only=True,
        ),
    ],
    tags=["portfolio"],
)


# --- Snapshots ---


snapshot_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Список снимков рынка",
        responses={200: SnapshotSerializer(many=True)},
        tags=["snapshots"],
    ),
    retrieve=extend_schema(
        summary="Снимок рынка",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID снимка.",
            ),
        ],
        responses={
            200: SnapshotSerializer,
            404: OpenApiResponse(description="Снимок не найден"),
        },
        tags=["snapshots"],
    ),
)


# --- Analytics ---


market_stats_schema = extend_schema(
    summary="Агрегированная статистика рынка",
    description="Считает min/max/avg цены и суммарную капитализацию "
    "по последнему снимку.",
    responses={
        200: MarketStatsSerializer,
        404: OpenApiResponse(
            response=error_response,
            description="Нет данных для анализа",
            examples=[
                OpenApiExample(
                    "Нет данных",
                    value={
                        "error": "No data available for analysis.",
                        "code": "no_data_for_analysis",
                    },
                    status_codes=["404"],
                ),
            ],
        ),
    },
    tags=["analytics"],
)


top_movers_schema = extend_schema(
    summary="Топ растущих и падающих монет",
    description="Возвращает топ-N монет по росту и падению "
    "за 24 часа из последнего снимка.",
    responses={
        200: TopMoversSerializer,
        404: OpenApiResponse(
            response=error_response,
            description="Нет данных для анализа",
            examples=[
                OpenApiExample(
                    "Нет данных",
                    value={
                        "error": "No data available for analysis.",
                        "code": "no_data_for_analysis",
                    },
                    status_codes=["404"],
                ),
            ],
        ),
    },
    tags=["analytics"],
)


volume_leaders_schema = extend_schema(
    summary="Лидеры по объёму торгов",
    description="Возвращает монеты с наибольшим объёмом торгов из последнего снимка.",
    responses={
        200: VolumeLeadersSerializer,
        404: OpenApiResponse(
            response=error_response,
            description="Нет данных для анализа",
            examples=[
                OpenApiExample(
                    "Нет данных",
                    value={
                        "error": "No data available for analysis.",
                        "code": "no_data_for_analysis",
                    },
                    status_codes=["404"],
                ),
            ],
        ),
    },
    tags=["analytics"],
)


# --- Tasks ---


task_status_schema = extend_schema(
    summary="Статус Celery-задачи",
    description=(
        "Возвращает текущий статус задачи по её id. Поля `result` и "
        "`failure_reason` присутствуют только для завершённых и упавших задач "
        "соответственно."
    ),
    parameters=[
        OpenApiParameter(
            name="task_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="UUID задачи, полученный при её постановке.",
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="TaskStatusResponse",
                fields={
                    "task_id": serializers.CharField(),
                    "status": serializers.CharField(),
                    "result": serializers.JSONField(required=False),
                    "failure_reason": serializers.CharField(required=False),
                },
            ),
            description="Статус задачи",
            examples=[
                OpenApiExample(
                    "В процессе",
                    value={"task_id": "f3a1...", "status": "STARTED"},
                    status_codes=["200"],
                ),
                OpenApiExample(
                    "Успех",
                    value={"task_id": "f3a1...", "status": "SUCCESS", "result": 42},
                    status_codes=["200"],
                ),
                OpenApiExample(
                    "Ошибка",
                    value={
                        "task_id": "f3a1...",
                        "status": "FAILURE",
                        "failure_reason": "Task failed.",
                    },
                    status_codes=["200"],
                ),
            ],
        ),
    },
    tags=["tasks"],
)


fetch_snapshot_schema = extend_schema(
    summary="Запустить сбор снимка рынка",
    description=(
        "Ставит в очередь Celery-задачу, которая опрашивает выбранный провайдер "
        "и сохраняет новый снимок рынка с ценами монет. Доступно только "
        "пользователям с правами staff."
    ),
    request=FetchSnapshotSerializer,
    responses={
        202: OpenApiResponse(
            response=task_accepted_response,
            description="Задача поставлена в очередь",
            examples=[
                OpenApiExample(
                    "Принято",
                    value={"task_id": "f3a1b2c3-7e89-4abc-9d10-1122334455aa"},
                    status_codes=["202"],
                ),
            ],
        ),
        401: OpenApiResponse(description="Требуется аутентификация"),
        403: OpenApiResponse(description="Доступно только staff-пользователям"),
    },
    examples=[
        OpenApiExample(
            "CoinGecko",
            value={"source": "coingecko"},
            request_only=True,
        ),
        OpenApiExample(
            "CoinMarketCap",
            value={"source": "cmc"},
            request_only=True,
        ),
    ],
    tags=["tasks"],
)
