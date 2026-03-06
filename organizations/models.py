from uuid import uuid4
from django.contrib.auth.models import AbstractUser
from django.db import models

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class User(AbstractUser):
    # Use UUID instead of integer ID
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # Custom fields
    organization = models.ForeignKey(
        'Organization', 
        on_delete=models.CASCADE, 
        related_name='users'
    )
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username # Or self.email