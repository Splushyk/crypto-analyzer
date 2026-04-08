from rest_framework import viewsets, generics
from rest_framework.pagination import PageNumberPagination

from crypto.models import Snapshot, CoinPrice
from crypto.serializers import SnapshotSerializer, CoinPriceSerializer


class SnapshotPagination(PageNumberPagination):
    page_size = 2


class SnapshotViewSet(viewsets.ModelViewSet):
    queryset = Snapshot.objects.all().order_by('-created_at')
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
