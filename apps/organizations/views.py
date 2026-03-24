from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from .models import Organization
from .serializers import UnverifiedOrganizationListSerializer
from utils.paginations import CustomPagination
from utils.api_response import APIResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

# View to list unverified organizations for admin review
class UnverifiedOrganizationListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        search=request.query_params.get("search", "")
        organizations = Organization.objects.filter(
            is_verified=False
        ).order_by("-created_at")

        if search:
            organizations = organizations.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(id__icontains=search)|
                Q(phone__icontains=search)
            )

        paginator = self.pagination_class()
        paginated_organizations = paginator.paginate_queryset(organizations, request, view=self)
        serializer = UnverifiedOrganizationListSerializer(paginated_organizations, many=True, context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
            message="Unverified organizations retrieved successfully."
        )
        
        


# View to approve an organization
class ApproveOrganizationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)

        if organization.is_verified:
            return APIResponse.error(
                message="Organization already verified.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        organization.is_verified = True
        organization.verified_at = timezone.now()
        organization.verified_by = request.user
        organization.save(update_fields=["is_verified", "verified_at", "verified_by"])
        
        verified_by_display = request.user.name or request.user.email

        return APIResponse.success(
            message="Organization approved successfully.",
            data={
                "id": organization.id,
                "name": organization.name,
                "is_verified": organization.is_verified,
                "verified_at": organization.verified_at,
                "verified_by": verified_by_display,
            },
            status_code=status.HTTP_200_OK
        )
        
        
 # View to reject an organization       
class RejectOrganizationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)

        organization.is_active = False
        organization.save(update_fields=["is_active"])

        return APIResponse.success(
            message="Organization rejected successfully.",
           data={},
            status_code=status.HTTP_200_OK
        )