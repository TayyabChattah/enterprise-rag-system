from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SessionChatViewSet

router = DefaultRouter()
router.register(r"sessions", SessionChatViewSet, basename="chat-session")

urlpatterns = [
    path("", include(router.urls)),
]
