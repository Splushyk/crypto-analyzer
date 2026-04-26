"""Кастомные DRF-пагинации для эндпоинтов crypto."""

from rest_framework.pagination import CursorPagination, PageNumberPagination


class CoinPriceCursorPagination(CursorPagination):
    page_size = 50
    ordering = "-id"


class SnapshotPagination(PageNumberPagination):
    """Маленькая страница: каждый снимок несёт 50 вложенных prices."""

    page_size = 2
