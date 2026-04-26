import django_filters

from crypto.models import CoinPrice


class CoinPriceFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(
        field_name="symbol",
        lookup_expr="iexact",
        help_text="Тикер монеты (точное совпадение).",
    )
    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
        help_text="Нижняя граница цены, включительно.",
    )
    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
        help_text="Верхняя граница цены, включительно.",
    )

    class Meta:
        model = CoinPrice
        fields = ["symbol", "min_price", "max_price"]
