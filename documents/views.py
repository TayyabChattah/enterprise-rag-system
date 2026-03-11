from django.shortcuts import render

from rest_framework.response import Response

from rest_framework import viewsets

from documents.tasks import process_document
from .serializers import DocumentSerializer, DocumentChunkSerializer
from .models import Document, DocumentChunk
from rest_framework.permissions import IsAuthenticated


class DocumentViewSet(viewsets.ModelViewSet):    
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(is_active=True, organization=self.request.user.organization)
    
    def perform_create(self, serializer):

        document = serializer.save(
            organization=self.request.user.organization,
            uploaded_by=self.request.user
        )

        process_document.delay(str(document.id))

class DocumentChunkViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentChunkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DocumentChunk.objects.filter(is_active=True, organization=self.request.user.organization)
    
class SearchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        from .services.vector_search import search_similar_chunks
        from .serializers import SearchSerializer

        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['query']

        results = search_similar_chunks(query, organization_id=request.user.organization_id)

        chunk_serializer = DocumentChunkSerializer(results, many=True)

        return Response(chunk_serializer.data)