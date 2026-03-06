from uuid import uuid4
from django.contrib.auth.models import AbstractUser
from django.db import models

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class User(AbstractUser):
    # Use UUID instead of integer ID
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # Custom fields
    organization = models.ForeignKey(
        'Organization', 
        on_delete=models.CASCADE, 
        related_name='users',
        blank=True,
        null=True
    )
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.username # Or self.email