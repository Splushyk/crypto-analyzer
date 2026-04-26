from celery.result import AsyncResult
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from crypto.exceptions import (
    NoDataForAnalysisError,
    SymbolNotFoundOnExchangeError,
    WatchlistDuplicateError,
    WatchlistItemNotFoundError,
)
from crypto.filters import CoinPriceFilter
from crypto.models import CoinPrice, Snapshot
from crypto.pagination import CoinPriceCursorPagination, SnapshotPagination
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


@snapshot_viewset_schema
class SnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Snapshot.objects.order_by("-created_at").prefetch_related("prices")
    serializer_class = SnapshotSerializer
    pagination_class = SnapshotPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "total_market_cap"]


@coin_history_schema
class CoinPriceHistoryView(generics.ListAPIView):
    serializer_class = CoinPriceSerializer
    filterset_class = CoinPriceFilter
    filter_backends = [DjangoFilterBackend]
    queryset = CoinPrice.objects.all()
    pagination_class = CoinPriceCursorPagination


class WatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    @watchlist_get_schema
    def get(self, request: Request, **kwargs) -> Response:
        assert request.user.is_authenticated
        user_watchlist = get_user_watchlist(request.user)
        serializer = WatchlistSerializer(user_watchlist, many=True)
        return Response(serializer.data)

    @watchlist_post_schema
    def post(self, request: Request, **kwargs) -> Response:
        assert request.user.is_authenticated
        serializer = AddToWatchlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        symbol = serializer.validated_data["symbol"]

        try:
            item = add_to_watchlist(request.user, symbol)
        except SymbolNotFoundError as exc:
            raise SymbolNotFoundOnExchangeError() from exc
        except ExistInWatchlistError as exc:
            raise WatchlistDuplicateError() from exc

        return Response(WatchlistSerializer(item).data, status=status.HTTP_201_CREATED)


class WatchlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @watchlist_delete_schema
    def delete(self, request: Request, symbol: str, **kwargs) -> Response:
        assert request.user.is_authenticated
        if not remove_from_watchlist(request.user, symbol):
            raise WatchlistItemNotFoundError()
        return Response(status=status.HTTP_204_NO_CONTENT)


@market_stats_schema
class MarketStatsView(APIView):
    def get(self, request: Request, **kwargs) -> Response:
        stats = get_market_stats()
        if stats is None:
            raise NoDataForAnalysisError()
        serializer = MarketStatsSerializer(stats)
        return Response(serializer.data)


@top_movers_schema
class TopMoversView(APIView):
    def get(self, request: Request, **kwargs) -> Response:
        tops = get_top_movers()
        if tops is None:
            raise NoDataForAnalysisError()
        serializer = TopMoversSerializer(tops)
        return Response(serializer.data)


@volume_leaders_schema
class VolumeLeadersView(APIView):
    def get(self, request: Request, **kwargs) -> Response:
        leaders = get_volume_leaders()
        if leaders is None:
            raise NoDataForAnalysisError()
        serializer = VolumeLeadersSerializer(leaders)
        return Response(serializer.data)


@fetch_snapshot_schema
class FetchSnapshotView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def post(self, request: Request, **kwargs) -> Response:
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
    def get(self, request: Request, task_id: str, **kwargs) -> Response:
        result = AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "status": result.status,
        }
        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["failure_reason"] = "Task failed."
        return Response(response)
