from django.urls import path
from rest_framework.routers import DefaultRouter

from crypto.views import SnapshotViewSet, CoinPriceHistoryView, WatchlistView, WatchlistDetailView

router = DefaultRouter()
router.register(r'snapshots', SnapshotViewSet)

urlpatterns = router.urls + [
    path('coins/', CoinPriceHistoryView.as_view()),
    path('watchlist/', WatchlistView.as_view()),
    path('watchlist/<str:symbol>/', WatchlistDetailView.as_view()),
]
