from rest_framework import viewsets, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crypto.models import Snapshot, CoinPrice
from crypto.serializers import SnapshotSerializer, CoinPriceSerializer, WatchlistSerializer, AddToWatchlistSerializer, \
    MarketStatsSerializer
from crypto.services import get_user_watchlist, add_to_watchlist, SymbolNotFoundError, ExistInWatchlistError, \
    remove_from_watchlist, get_market_stats


class SnapshotPagination(PageNumberPagination):
    page_size = 2


class SnapshotViewSet(viewsets.ModelViewSet):
    queryset = Snapshot.objects.order_by('-created_at').prefetch_related('prices')
    serializer_class = SnapshotSerializer
    pagination_class = SnapshotPagination
    http_method_names = ['get', 'head', 'options']


class CoinPriceHistoryView(generics.ListAPIView):
    serializer_class = CoinPriceSerializer

    def get_queryset(self):
        symbol = self.request.query_params.get('symbol')
        if symbol is None:
            return CoinPrice.objects.all().order_by('-snapshot__created_at')

        return CoinPrice.objects.filter(symbol=symbol).order_by('-snapshot__created_at')


class WatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_watchlist = get_user_watchlist(request.user)
        serializer = WatchlistSerializer(user_watchlist, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AddToWatchlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        symbol = serializer.validated_data['symbol']

        try:
            item = add_to_watchlist(request.user, symbol)
        except SymbolNotFoundError:
            return Response(
                {"error": "Символ не найден на бирже"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ExistInWatchlistError:
            return Response(
                {"error": "Монета уже в вашем списке отслеживаемых монет"},
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            WatchlistSerializer(item).data,
            status=status.HTTP_201_CREATED
        )


class WatchlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, symbol):
        if remove_from_watchlist(request.user, symbol):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"error": "Такой монеты не было в вашем списке отслеживаемых монет"},
                status=status.HTTP_404_NOT_FOUND
            )


class MarketStatsView(APIView):
    def get(self, request):
        stats = get_market_stats()
        if stats is None:
            return Response(
                {"error": "Нет данных для анализа"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MarketStatsSerializer(stats)
        return Response(serializer.data)
