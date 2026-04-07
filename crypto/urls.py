from rest_framework.routers import DefaultRouter

from crypto.views import SnapshotViewSet

router = DefaultRouter()
router.register(r'snapshots', SnapshotViewSet)

urlpatterns = router.urls
