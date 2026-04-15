from django.urls import path
from rest_framework.routers import DefaultRouter

from crypto.views import SnapshotViewSet, CoinPriceHistoryView, WatchlistView, WatchlistDetailView, MarketStatsView, \
    TopMoversView

router = DefaultRouter()
router.register(r'snapshots', SnapshotViewSet)

urlpatterns = router.urls + [
    path('coins/', CoinPriceHistoryView.as_view()),
    path('watchlist/', WatchlistView.as_view()),
    path('watchlist/<str:symbol>/', WatchlistDetailView.as_view()),
    path('analytics/market-stats/', MarketStatsView.as_view()),
    path('analytics/top-movers/', TopMoversView.as_view()),
]
