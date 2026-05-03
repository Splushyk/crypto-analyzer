"""DRF throttle-классы по ролям пользователя."""

from rest_framework.throttling import UserRateThrottle


class SuperUserRateThrottle(UserRateThrottle):
    """Лимит для суперюзеров."""

    scope = "superuser"

    def get_cache_key(self, request, view):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return None
        return super().get_cache_key(request, view)


class CustomUserRateThrottle(UserRateThrottle):
    """Лимит для обычных авторизованных юзеров."""

    def get_cache_key(self, request, view):
        if request.user.is_authenticated and request.user.is_superuser:
            return None
        return super().get_cache_key(request, view)
