import secrets
from datetime import timedelta

from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from rest_framework import serializers

from .models import Organization, OrganizationInvitation, User


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data.get("name", ""))

        max_len = Organization._meta.get_field("slug").max_length or 50
        validated_data["slug"] = (validated_data.get("slug") or "")[:max_len].strip("-")
        return super().create(validated_data)


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "organization", "role", "is_active"]
        read_only_fields = fields


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = User
        fields = ["id", "email", "password", "role", "is_active"]
        read_only_fields = ["id"]

    def validate_email(self, value: str):
        return value.strip().lower()

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        return attrs

    def validate_role(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return value
        if user.is_superuser or getattr(user, "role", None) == "admin":
            return value
        if self.instance and value != getattr(self.instance, "role", None):
            raise serializers.ValidationError("Only org admins can change roles.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        return User.objects.create_user(**validated_data, password=password)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class OrganizationRegistrationSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    organization_slug = serializers.SlugField(required=False, allow_blank=True)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, min_length=8)

    def validate_admin_email(self, value: str):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def _unique_slug(self, base: str) -> str:
        max_len = Organization._meta.get_field("slug").max_length or 50

        base = slugify(base or "").strip("-")
        if not base:
            base = f"org-{secrets.token_hex(3)}"

        base = base[:max_len].strip("-") or f"org-{secrets.token_hex(3)}"[:max_len].strip("-")

        slug = base[:max_len]
        for _ in range(10):
            if slug and not Organization.objects.filter(slug=slug).exists():
                return slug

            suffix = secrets.token_hex(2)
            head_max = max_len - (1 + len(suffix))
            head = (base[: max(0, head_max)] or "org").strip("-")
            slug = f"{head}-{suffix}"[:max_len].strip("-")

        suffix = secrets.token_hex(6)
        head_max = max_len - (1 + len(suffix))
        head = (base[: max(0, head_max)] or "org").strip("-")
        return f"{head}-{suffix}"[:max_len].strip("-")

    def create(self, validated_data):
        org_name = validated_data["organization_name"].strip()
        requested_slug = (validated_data.get("organization_slug") or "").strip()
        org_slug = self._unique_slug(requested_slug or org_name)

        org = Organization.objects.create(name=org_name, slug=org_slug)

        admin_email = validated_data["admin_email"]
        admin_password = validated_data["admin_password"]

        user = User.objects.create_user(
            email=admin_email,
            password=admin_password,
            organization=org,
            role="admin",
            is_active=True,
        )

        return {"organization": org, "user": user}


class InvitationCreateSerializer(serializers.ModelSerializer):
    expires_in_days = serializers.IntegerField(required=False, min_value=1, max_value=30, default=7, write_only=True)

    class Meta:
        model = OrganizationInvitation
        fields = ["id", "email", "role", "expires_in_days"]
        read_only_fields = ["id"]

    def validate_email(self, value: str):
        return value.strip().lower()

    def create(self, validated_data):
        expires_in_days = validated_data.pop("expires_in_days", 7)
        invitation = OrganizationInvitation.objects.create(
            **validated_data,
            expires_at=timezone.now() + timedelta(days=expires_in_days),
        )
        return invitation


class InvitationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationInvitation
        fields = [
            "id",
            "organization",
            "email",
            "role",
            "status",
            "invited_by",
            "invited_at",
            "accepted_by",
            "accepted_at",
            "revoked_at",
            "expires_at",
        ]
        read_only_fields = fields


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_token(self, value: str):
        return (value or "").strip()


class InvitationCreatedResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    token = serializers.CharField()
    accept_url = serializers.CharField()

    @staticmethod
    def build(invitation: OrganizationInvitation) -> dict:
        base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
        accept_url = f"{base}/accept-invite?token={invitation.token}" if base else f"/api/auth/invitations/accept/"

        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
            "token": invitation.token,
            "accept_url": accept_url,
        }
