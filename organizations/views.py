from urllib import request

from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets

from organizations.serializers import OrganizationSerializer
from .models import Organization, User
from .serializers import OrganizationSerializer, UserSerializer

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().filter(is_active=True)
    serializer_class = OrganizationSerializer

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        user=self.request.user
        return User.objects.filter(is_active=True, organization=user.organization)


