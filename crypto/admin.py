from django.contrib import admin
from django.utils.html import format_html

from crypto.models import CoinPrice, Snapshot, WatchlistItem


class CoinPriceInline(admin.TabularInline):
    model = CoinPrice
    verbose_name_plural = "Список цен на момент снимка"
    extra = 0  # Чтобы Django не создавал пустые строки для новых записей по умолчанию
    fields = (
        "symbol",
        "name",
        "formatted_price",
        "formatted_change",
        "formatted_market_cap",
        "formatted_volume",
    )
    # Запрещаем редактирование всех важных данных
    readonly_fields = fields

    # Это скроет кнопку "Add another Coin Price" внизу таблицы,
    # так как мы не должны добавлять монеты вручную вне парсера
    def has_add_permission(self, request, obj=None):
        return False

    # Убираем колонку "Удалить" (чекбоксы)
    def has_delete_permission(self, request, obj=None):
        return False

    # Метод для цены
    @admin.display(description="Цена ($)")
    def formatted_price(self, obj):
        # f-строка с 6 знаками после запятой и разделителем тысяч
        return f"{obj.price:,.6f}"

    # Метод для капитализации (с разделением тысяч)
    @admin.display(description="Капитализация")
    def formatted_market_cap(self, obj):
        return f"${obj.market_cap:,.0f}"

    # Метод для объема
    @admin.display(description="Объем (24ч)")
    def formatted_volume(self, obj):
        return f"${obj.volume:,.0f}"

    # Метод для процентов (с цветом)
    @admin.display(description="Изменение (24ч)")
    def formatted_change(self, obj):
        color = "green" if obj.change_24h >= 0 else "red"
        # Сначала готовим текст с процентами
        change_text = f"{obj.change_24h:+.2f}%"
        # Потом передаем готовую строку в HTML
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, change_text
        )


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "formatted_total_cap")
    ordering = ("-created_at",)
    inlines = [CoinPriceInline]

    @admin.display(description="Общая капитализация")
    def formatted_total_cap(self, obj):
        return f"${obj.total_market_cap:,.0f}"


@admin.register(CoinPrice)
class CoinPriceAdmin(admin.ModelAdmin):
    # Используем те же красивые методы, что и в инлайне
    list_display = ("symbol", "name", "formatted_price", "formatted_change", "snapshot")
    list_filter = ("symbol", "snapshot")
    search_fields = ("symbol", "name")

    # Делаем поля нередактируемыми
    readonly_fields = (
        "snapshot",
        "name",
        "symbol",
        "price",
        "change_24h",
        "volume",
        "market_cap",
    )

    @admin.display(description="Цена")
    def formatted_price(self, obj):
        return f"${obj.price:,.6f}"

    @admin.display(description="24ч %")
    def formatted_change(self, obj):
        color = "green" if obj.change_24h >= 0 else "red"
        # Аналогично: сначала форматируем число
        change_text = f"{obj.change_24h:+.2f}%"
        return format_html('<span style="color: {};">{}</span>', color, change_text)


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "symbol", "coin_name", "added_at")
    list_filter = ("user", "symbol", "added_at")
    search_fields = ("user__username", "symbol")
    readonly_fields = ("added_at",)


admin.site.site_header = "Панель управления Crypto Analyzer"  # Текст в синей шапке
admin.site.site_title = "Crypto Analyzer"  # Текст во вкладке браузера
admin.site.index_title = "Аналитика крипторынка"  # Текст на главной странице админки
