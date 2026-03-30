from django.contrib import admin
from .models import Snapshot, CoinPrice


class CoinPriceInline(admin.TabularInline):
    model = CoinPrice
    extra = 0  # Чтобы Django не создавал пустые строки для новых записей по умолчанию
    readonly_fields = ('symbol', 'price', 'change_24h')


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'total_market_cap')
    ordering = ('-created_at',)
    inlines = [CoinPriceInline]


@admin.register(CoinPrice)
class CoinPriceAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'price', 'change_24h', 'snapshot')
    list_filter = ('symbol', 'snapshot')
    search_fields = ('symbol', 'name')
