from django.conf import settings
from django.db import models
from django.utils import timezone


class Snapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    total_market_cap = models.DecimalField(max_digits=25, decimal_places=2, verbose_name="Общая капитализация")

    class Meta:
        verbose_name = "Снимок рынка"
        verbose_name_plural = "Снимки рынка"

    def __str__(self):
        local_time = timezone.localtime(self.created_at)
        return local_time.strftime('%d.%m.%Y %H:%M:%S')


class CoinPrice(models.Model):
    snapshot = models.ForeignKey(
        Snapshot,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name="Снимок",
    )

    name = models.CharField(max_length=100, verbose_name="Название")
    symbol = models.CharField(max_length=20, verbose_name="Символ")
    price = models.DecimalField("Цена ($)", max_digits=20, decimal_places=6)
    change_24h = models.FloatField(verbose_name="Изменение (24ч)")
    volume = models.DecimalField(max_digits=25, decimal_places=2, verbose_name="Объем (24ч)")
    market_cap = models.DecimalField(max_digits=25, decimal_places=2, verbose_name="Капитализация")

    class Meta:
        verbose_name = "Цена монеты"
        verbose_name_plural = "Цены монет"

    def __str__(self):
        return f"{self.symbol} - {self.price}"


class WatchlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='watchlist',
        verbose_name="Пользователь",
    )

    symbol = models.CharField(max_length=20, verbose_name="Символ")
    coin_name = models.CharField(max_length=100, verbose_name="Название")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Начало отслеживания")

    class Meta:
        verbose_name = "Список отслеживаемых монет"
        verbose_name_plural = "Списки отслеживаемых монет"
        ordering = ["-added_at"]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'symbol'],
                name='unique_symbol_for_user')
        ]

    def __str__(self):
        local_time = timezone.localtime(self.added_at)
        return f"{self.user.username}: {self.symbol} - {local_time.strftime('%d.%m.%Y %H:%M:%S')}"
