from .views import DocumentChunkViewSet, DocumentViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'document-chunks', DocumentChunkViewSet, basename='documentchunk')

urlpatterns = [
    path('', include(router.urls)),
]