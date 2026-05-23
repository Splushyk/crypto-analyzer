from django.urls import path
from rest_framework.routers import DefaultRouter

from crypto.views import (
    BuyCoinView,
    CoinPriceHistoryView,
    FetchSnapshotView,
    MarketStatsView,
    PortfolioHistoryView,
    PortfolioView,
    SellPositionView,
    SnapshotViewSet,
    TaskStatusView,
    TopMoversView,
    VolumeLeadersView,
    WatchlistDetailView,
    WatchlistView,
)

router = DefaultRouter()
router.register(r"snapshots", SnapshotViewSet)

urlpatterns = router.urls + [
    path("coins/", CoinPriceHistoryView.as_view()),
    path("watchlist/", WatchlistView.as_view()),
    path("watchlist/<str:symbol>/", WatchlistDetailView.as_view()),
    path("analytics/market-stats/", MarketStatsView.as_view()),
    path("analytics/top-movers/", TopMoversView.as_view()),
    path("analytics/volume-leaders/", VolumeLeadersView.as_view()),
    path("portfolio/", PortfolioView.as_view()),
    path("portfolio/history/", PortfolioHistoryView.as_view()),
    path("portfolio/buy/", BuyCoinView.as_view()),
    path(
        "portfolio/positions/<int:position_id>/sell/",
        SellPositionView.as_view(),
    ),
    path("tasks/fetch-snapshot/", FetchSnapshotView.as_view()),
    path("tasks/<str:task_id>/status/", TaskStatusView.as_view()),
]
