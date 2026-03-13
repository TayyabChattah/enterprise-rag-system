from django.contrib import admin

from .models import Organization, OrganizationInvitation, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "organization", "role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email",)
    list_filter = ("role", "is_active", "is_staff", "is_superuser")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "email", "role", "status", "invited_at", "expires_at")
    search_fields = ("email", "organization__name", "organization__slug")
    list_filter = ("status", "role", "organization")
