from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Snapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    total_market_cap = models.DecimalField(
        max_digits=25, decimal_places=2, verbose_name="Общая капитализация"
    )

    class Meta:
        verbose_name = "Снимок рынка"
        verbose_name_plural = "Снимки рынка"

    def __str__(self):
        local_time = timezone.localtime(self.created_at)
        return local_time.strftime("%d.%m.%Y %H:%M:%S")


class CoinPrice(models.Model):
    snapshot = models.ForeignKey(
        Snapshot,
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name="Снимок",
    )

    name = models.CharField(max_length=100, verbose_name="Название")
    symbol = models.CharField(max_length=20, verbose_name="Символ")
    price = models.DecimalField("Цена ($)", max_digits=20, decimal_places=6)
    change_24h = models.FloatField(verbose_name="Изменение (24ч)")
    volume = models.DecimalField(
        max_digits=25, decimal_places=2, verbose_name="Объем (24ч)"
    )
    market_cap = models.DecimalField(
        max_digits=25, decimal_places=2, verbose_name="Капитализация"
    )

    class Meta:
        verbose_name = "Цена монеты"
        verbose_name_plural = "Цены монет"

    def __str__(self):
        return f"{self.symbol} - {self.price}"


class Portfolio(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio",
        verbose_name="Пользователь",
    )
    symbol = models.CharField(max_length=20, db_index=True, verbose_name="Символ")
    amount = models.DecimalField(
        max_digits=20, decimal_places=8, verbose_name="Количество"
    )
    buy_price = models.DecimalField("Цена покупки ($)", max_digits=20, decimal_places=6)
    bought_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата покупки")

    class Meta:
        verbose_name = "Позиция портфеля"
        verbose_name_plural = "Позиции портфеля"
        ordering = ["-bought_at"]

    def __str__(self):
        return f"{self.user.username}: {self.symbol} x {self.amount} @ {self.buy_price}"


class Balance(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="balance",
        verbose_name="Пользователь",
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Баланс ($)",
    )

    class Meta:
        verbose_name = "Баланс пользователя"
        verbose_name_plural = "Балансы пользователей"

    def __str__(self):
        return f"{self.user.username}: ${self.amount}"


class WatchlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watchlist",
        verbose_name="Пользователь",
    )

    symbol = models.CharField(max_length=20, verbose_name="Символ")
    coin_name = models.CharField(max_length=100, verbose_name="Название")
    added_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Начало отслеживания"
    )

    class Meta:
        verbose_name = "Список отслеживаемых монет"
        verbose_name_plural = "Списки отслеживаемых монет"
        ordering = ["-added_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "symbol"], name="unique_symbol_for_user"
            )
        ]

    def __str__(self):
        local_time = timezone.localtime(self.added_at)
        local_time_str = local_time.strftime("%d.%m.%Y %H:%M:%S")
        return f"{self.user.username}: {self.symbol} - {local_time_str}"
