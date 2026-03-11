from .views import DocumentChunkViewSet, DocumentViewSet, SearchViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'document-chunks', DocumentChunkViewSet, basename='documentchunk')
router.register(r'search', SearchViewSet, basename='search')

urlpatterns = [
    path('', include(router.urls)),
]