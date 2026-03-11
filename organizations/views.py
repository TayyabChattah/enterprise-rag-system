from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Organization, User
from .permissions import IsOrgAdmin, IsPlatformAdmin
from .serializers import OrganizationSerializer, UserReadSerializer, UserWriteSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsPlatformAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Organization.objects.filter(is_active=True)
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return qs
        if getattr(user, "organization_id", None):
            return qs.filter(id=user.organization_id)
        return qs.none()


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return UserReadSerializer
        return UserWriteSerializer

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.filter(is_active=True)
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return qs
        if not getattr(user, "organization_id", None):
            return qs.none()
        if getattr(user, "role", None) == "admin":
            return qs.filter(organization_id=user.organization_id)
        return qs.filter(id=user.id)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
