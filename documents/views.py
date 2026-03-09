from django.shortcuts import render

from rest_framework import viewsets
from .serializers import DocumentSerializer, DocumentChunkSerializer
from .models import Document, DocumentChunk
from rest_framework.permissions import IsAuthenticated


class DocumentViewSet(viewsets.ModelViewSet):    
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(is_active=True, organization=self.request.user.organization)
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization, uploaded_by=self.request.user)

class DocumentChunkViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentChunkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DocumentChunk.objects.filter(is_active=True, organization=self.request.user.organization)