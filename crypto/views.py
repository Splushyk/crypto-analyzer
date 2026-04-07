from rest_framework import viewsets, generics

from crypto.models import Snapshot, CoinPrice
from crypto.serializers import SnapshotSerializer, CoinPriceSerializer


class SnapshotViewSet(viewsets.ModelViewSet):
    queryset = Snapshot.objects.all()
    serializer_class = SnapshotSerializer
    http_method_names = ['get', 'head', 'options']


class CoinPriceHistoryView(generics.ListAPIView):
    def get_queryset(self):
        symbol = self.request.query_params.get('symbol')
        return CoinPrice.objects.filter(symbol=symbol)

    serializer_class = CoinPriceSerializer
