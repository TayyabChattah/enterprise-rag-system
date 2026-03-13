from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from .models import Organization, OrganizationInvitation, User
from .permissions import HasOrganization, IsOrgAdmin, IsPlatformAdmin
from .serializers import (
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationCreatedResponseSerializer,
    InvitationReadSerializer,
    OrganizationRegistrationSerializer,
    OrganizationSerializer,
    UserReadSerializer,
    UserWriteSerializer,
)


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


class OrganizationRegistrationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OrganizationRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                description="Organization + admin user created. Then call /api/auth/login/ to obtain JWT tokens."
            )
        },
        tags=["auth"],
        operation_id="auth_register_org",
    )
    def post(self, request):
        serializer = OrganizationRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            created = serializer.save()

        org = created["organization"]
        user = created["user"]

        return Response(
            {
                "organization": {"id": str(org.id), "name": org.name, "slug": org.slug},
                "admin_user": {"id": str(user.id), "email": user.email, "role": user.role},
                "next": {"login": "/api/auth/login/"},
            },
            status=status.HTTP_201_CREATED,
        )


class InvitationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdmin, HasOrganization]

    def get_queryset(self):
        return OrganizationInvitation.objects.filter(organization_id=self.request.user.organization_id).order_by("-invited_at")

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return InvitationReadSerializer
        return InvitationCreateSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization, invited_by=self.request.user)

    @extend_schema(
        request=InvitationCreateSerializer,
        responses={
            201: InvitationCreatedResponseSerializer,
            400: OpenApiResponse(description="Validation error / duplicate pending invite."),
            403: OpenApiResponse(description="Forbidden (requires org admin)."),
        },
        tags=["organizations"],
        operation_id="organizations_invite_create",
    )
    def create(self, request, *args, **kwargs):
        try:
            resp = super().create(request, *args, **kwargs)
        except IntegrityError:
            email = (request.data.get("email", "") or "").strip().lower()
            existing = (
                OrganizationInvitation.objects.filter(
                    organization_id=request.user.organization_id,
                    email=email,
                    status=OrganizationInvitation.STATUS_PENDING,
                )
                .order_by("-invited_at")
                .first()
            )
            if existing and existing.is_expired():
                existing.status = OrganizationInvitation.STATUS_EXPIRED
                existing.save(update_fields=["status"])
                resp = super().create(request, *args, **kwargs)
            else:
                return Response({"detail": "An active pending invite already exists for this email."}, status=400)

        invitation = OrganizationInvitation.objects.get(id=resp.data["id"])
        payload = InvitationCreatedResponseSerializer.build(invitation)
        return Response(payload, status=201)

    def destroy(self, request, *args, **kwargs):
        invitation = self.get_object()
        if invitation.status != OrganizationInvitation.STATUS_PENDING:
            return Response({"detail": "Only pending invitations can be revoked."}, status=400)

        if invitation.is_expired():
            invitation.status = OrganizationInvitation.STATUS_EXPIRED
            invitation.save(update_fields=["status"])
            return Response({"detail": "Invitation is already expired."}, status=400)

        invitation.status = OrganizationInvitation.STATUS_REVOKED
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["status", "revoked_at"])
        return Response(status=204)


class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=InvitationAcceptSerializer,
        responses={
            200: OpenApiResponse(description="Invitation accepted. Then call /api/auth/login/ to obtain JWT tokens."),
            400: OpenApiResponse(description="Invalid/expired/revoked token."),
            409: OpenApiResponse(description="Email already belongs to another organization."),
        },
        tags=["auth"],
        operation_id="auth_invitation_accept",
    )
    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        try:
            invitation = OrganizationInvitation.objects.select_related("organization").get(token=token)
        except OrganizationInvitation.DoesNotExist:
            return Response({"detail": "Invalid invitation token."}, status=400)

        if invitation.status != OrganizationInvitation.STATUS_PENDING:
            return Response({"detail": f"Invitation is not pending (status={invitation.status})."}, status=400)

        if invitation.is_expired():
            invitation.status = OrganizationInvitation.STATUS_EXPIRED
            invitation.save(update_fields=["status"])
            return Response({"detail": "Invitation has expired."}, status=400)

        with transaction.atomic():
            email = invitation.email.strip().lower()
            user = User.objects.filter(email=email).first()

            if user:
                if user.organization_id and user.organization_id != invitation.organization_id:
                    return Response({"detail": "This email is already registered under another organization."}, status=409)

                if not user.organization_id:
                    user.organization = invitation.organization

                user.role = invitation.role
                user.is_active = True
                user.set_password(password)
                user.save(update_fields=["organization", "role", "is_active", "password"])
            else:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    organization=invitation.organization,
                    role=invitation.role,
                    is_active=True,
                )

            invitation.status = OrganizationInvitation.STATUS_ACCEPTED
            invitation.accepted_by = user
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["status", "accepted_by", "accepted_at"])

        return Response(
            {
                "detail": "Invitation accepted.",
                "organization_id": str(invitation.organization_id),
                "user_id": str(user.id),
                "next": {"login": "/api/auth/login/"},
            },
            status=200,
        )
