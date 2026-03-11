from .models import Document, DocumentChunk
from rest_framework import serializers
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document    
        fields = ['id', 'file', 'created_at','updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'document','content', 'created_at']
        read_only_fields = ['id', 'created_at']


class SearchSerializer(serializers.Serializer):
    query = serializers.CharField()

