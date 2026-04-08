from rest_framework import serializers

from crypto.models import CoinPrice, Snapshot


class CoinPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPrice
        fields = ['id', 'name', 'symbol', 'price', 'change_24h',
                  'volume', 'market_cap']


class SnapshotSerializer(serializers.ModelSerializer):
    prices = CoinPriceSerializer(many=True, read_only=True)

    class Meta:
        model = Snapshot
        fields = ['id', 'created_at', 'total_market_cap', 'prices']
