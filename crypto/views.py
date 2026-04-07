from rest_framework import viewsets

from crypto.models import Snapshot
from crypto.serializers import SnapshotSerializer


class SnapshotViewSet(viewsets.ModelViewSet):
    queryset = Snapshot.objects.all()
    serializer_class = SnapshotSerializer
    http_method_names = ['get', 'head', 'options']
