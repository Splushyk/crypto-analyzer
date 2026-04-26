from rest_framework.pagination import CursorPagination


class CoinPriceCursorPagination(CursorPagination):
    page_size = 50
    ordering = "-id"
