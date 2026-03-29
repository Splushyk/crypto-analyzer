from django.db import models


class Snapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total_market_cap = models.FloatField()

    def __str__(self):
        return f"Snapshot {self.id} at {self.created_at}"


class CoinPrice(models.Model):
    snapshot = models.ForeignKey(
        Snapshot,
        on_delete=models.CASCADE,
        related_name='prices'
    )

    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    price = models.FloatField()
    change_24h = models.FloatField()
    volume = models.FloatField()
    market_cap = models.FloatField()

    def __str__(self):
        return f"{self.symbol} - {self.price}"
