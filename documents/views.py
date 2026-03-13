from django.shortcuts import render

from rest_framework.response import Response

from rest_framework import viewsets
from drf_spectacular.utils import OpenApiResponse, extend_schema

from documents.tasks import process_document
from .serializers import DocumentChunkSerializer, DocumentSerializer, SearchSerializer
from .models import Document, DocumentChunk
from rest_framework.permissions import IsAuthenticated
from organizations.permissions import HasOrganization, IsOrgAdmin
from rest_framework.parsers import FormParser, MultiPartParser


class DocumentViewSet(viewsets.ModelViewSet):    
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, HasOrganization]
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), HasOrganization(), IsOrgAdmin()]
        return [IsAuthenticated(), HasOrganization()]

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
    permission_classes = [IsAuthenticated, HasOrganization]

    def get_queryset(self):
        return DocumentChunk.objects.filter(is_active=True, organization=self.request.user.organization)
    
class SearchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasOrganization]

    @extend_schema(
        request=None,
        responses={405: OpenApiResponse(description="Use POST with a JSON body: { query: string }.")},
        tags=["documents"],
        operation_id="documents_search_invalid_get",
    )
    def list(self, request):
        return Response({"detail": "Method not allowed."}, status=405)

    @extend_schema(
        request=SearchSerializer,
        responses={200: DocumentChunkSerializer(many=True)},
        tags=["documents"],
        operation_id="documents_search",
    )
    def create(self, request):
        from .services.vector_search import search_similar_chunks

        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['query']

        results = search_similar_chunks(query, organization_id=request.user.organization_id)

        chunk_serializer = DocumentChunkSerializer(results, many=True)

        return Response(chunk_serializer.data)
