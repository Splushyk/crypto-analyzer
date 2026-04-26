from celery.result import AsyncResult
from django.db.models import QuerySet
from rest_framework import generics, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from crypto.models import CoinPrice, Snapshot
from crypto.permissions import IsAdminOrReadOnly
from crypto.schemas import (
    coin_history_schema,
    fetch_snapshot_schema,
    market_stats_schema,
    snapshot_viewset_schema,
    task_status_schema,
    top_movers_schema,
    volume_leaders_schema,
    watchlist_delete_schema,
    watchlist_get_schema,
    watchlist_post_schema,
)
from crypto.serializers import (
    AddToWatchlistSerializer,
    CoinPriceFilterSerializer,
    CoinPriceSerializer,
    FetchSnapshotSerializer,
    MarketStatsSerializer,
    SnapshotSerializer,
    TopMoversSerializer,
    VolumeLeadersSerializer,
    WatchlistSerializer,
)
from crypto.services import (
    ExistInWatchlistError,
    SymbolNotFoundError,
    add_to_watchlist,
    get_market_stats,
    get_top_movers,
    get_user_watchlist,
    get_volume_leaders,
    remove_from_watchlist,
)
from crypto.tasks import fetch_snapshot_task


class SnapshotPagination(PageNumberPagination):
    page_size = 2


@snapshot_viewset_schema
class SnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Snapshot.objects.order_by("-created_at").prefetch_related("prices")
    serializer_class = SnapshotSerializer
    pagination_class = SnapshotPagination


@coin_history_schema
class CoinPriceHistoryView(generics.ListAPIView):
    serializer_class = CoinPriceSerializer

    def get_queryset(self) -> QuerySet[CoinPrice]:
        filter_serializer = CoinPriceFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        filters = filter_serializer.validated_data

        queryset = CoinPrice.objects.all().order_by("-snapshot__created_at", "-id")
        if "symbol" in filters:
            queryset = queryset.filter(symbol=filters["symbol"])
        if "min_price" in filters:
            queryset = queryset.filter(price__gte=filters["min_price"])
        if "max_price" in filters:
            queryset = queryset.filter(price__lte=filters["max_price"])
        return queryset


class WatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    @watchlist_get_schema
    def get(self, request: Request) -> Response:
        assert request.user.is_authenticated
        user_watchlist = get_user_watchlist(request.user)
        serializer = WatchlistSerializer(user_watchlist, many=True)
        return Response(serializer.data)

    @watchlist_post_schema
    def post(self, request: Request) -> Response:
        assert request.user.is_authenticated
        serializer = AddToWatchlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        symbol = serializer.validated_data["symbol"]

        try:
            item = add_to_watchlist(request.user, symbol)
        except SymbolNotFoundError:
            return Response(
                {"error": "Символ не найден на бирже"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ExistInWatchlistError:
            return Response(
                {"error": "Монета уже в вашем списке отслеживаемых монет"},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(WatchlistSerializer(item).data, status=status.HTTP_201_CREATED)


class WatchlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @watchlist_delete_schema
    def delete(self, request: Request, symbol: str) -> Response:
        assert request.user.is_authenticated
        if remove_from_watchlist(request.user, symbol):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"error": "Такой монеты не было в вашем списке отслеживаемых монет"},
                status=status.HTTP_404_NOT_FOUND,
            )


@market_stats_schema
class MarketStatsView(APIView):
    def get(self, request: Request) -> Response:
        stats = get_market_stats()
        if stats is None:
            return Response(
                {"error": "Нет данных для анализа"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MarketStatsSerializer(stats)
        return Response(serializer.data)


@top_movers_schema
class TopMoversView(APIView):
    def get(self, request: Request) -> Response:
        tops = get_top_movers()
        if tops is None:
            return Response(
                {"error": "Нет данных для анализа"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TopMoversSerializer(tops)
        return Response(serializer.data)


@volume_leaders_schema
class VolumeLeadersView(APIView):
    def get(self, request: Request) -> Response:
        leaders = get_volume_leaders()
        if leaders is None:
            return Response(
                {"error": "Нет данных для анализа"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = VolumeLeadersSerializer(leaders)
        return Response(serializer.data)


@fetch_snapshot_schema
class FetchSnapshotView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def post(self, request: Request) -> Response:
        serializer = FetchSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data["source"]
        result = fetch_snapshot_task.delay(source)
        return Response(
            {"task_id": result.id},
            status=status.HTTP_202_ACCEPTED,
        )


@task_status_schema
class TaskStatusView(APIView):
    def get(self, request: Request, task_id: str) -> Response:
        result = AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "status": result.status,
        }
        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["error"] = "Задача завершилась с ошибкой"
        return Response(response)
