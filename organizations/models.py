from uuid import uuid4
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.db.models import Q
from django.utils import timezone

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    username = None   # ❗ Remove username field

    email = models.EmailField(unique=True)

    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='users',
        blank=True,
        null=True
    )

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')

    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()   # attach manager

    def __str__(self):
        return self.email


def _default_invite_expires_at():
    return timezone.now() + timedelta(days=7)


def _generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


class OrganizationInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default="member")

    token = models.CharField(max_length=128, unique=True, default=_generate_invite_token, editable=False)

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REVOKED = "revoked"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REVOKED, "Revoked"),
        (STATUS_EXPIRED, "Expired"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    invited_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    invited_at = models.DateTimeField(auto_now_add=True)

    accepted_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    revoked_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=_default_invite_expires_at)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                condition=Q(status="pending"),
                name="uniq_pending_invite_org_email",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["token"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    def __str__(self):
        return f"Invite {self.email} to {self.organization_id} ({self.status})"
        
