from rest_framework import serializers

from crypto.models import CoinPrice, Snapshot, WatchlistItem


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


class WatchlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchlistItem
        fields = ['id', 'symbol', 'coin_name', 'added_at']


class AddToWatchlistSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=20)


class MarketStatsSerializer(serializers.Serializer):
    min_price = serializers.DecimalField(max_digits=20, decimal_places=6)
    max_price = serializers.DecimalField(max_digits=20, decimal_places=6)
    avg_price = serializers.DecimalField(max_digits=22, decimal_places=8)
    total_market_cap = serializers.DecimalField(max_digits=25, decimal_places=2)


class TopMoversSerializer(serializers.Serializer):
    top_gainers = CoinPriceSerializer(many=True, read_only=True)
    top_losers = CoinPriceSerializer(many=True, read_only=True)


class VolumeLeadersSerializer(serializers.Serializer):
    leaders = CoinPriceSerializer(many=True, read_only=True)
