from uuid import uuid4
from pgvector.django import VectorField
from django.db import models

# Create your models here.
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='documents/')
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('error', 'Error'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    uploaded_by = models.ForeignKey('organizations.User', on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.file.name
    
class DocumentChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='document_chunks')
    content = models.TextField()
    
    embedding = VectorField(dimensions=768, null=True, blank=True)
    index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Chunk {self.id} of Document {self.document.id}"
    
    