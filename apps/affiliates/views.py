from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from django.db.models import Q

from .models import Affiliate
from .serializers import AffiliateListSerializer
from utils.paginations import CustomPagination
from utils.api_response import APIResponse
from .serializers import AffiliateStatusUpdateSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404    


class AffiliateListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")

        affiliates = Affiliate.objects.select_related("user").all()

        #search filter
        if search:
            affiliates = affiliates.filter(
                Q(user__name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(id__icontains=search)
            )

        # status filter
        if status_filter:
            affiliates = affiliates.filter(status=status_filter)

        affiliates = affiliates.order_by("-created_at")

        paginator = self.pagination_class()
        paginated_affiliates = paginator.paginate_queryset(affiliates, request, view=self)
        serializer = AffiliateListSerializer(paginated_affiliates, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="Affiliate list retrieved successfully."
        )
        
        
 

class UpdateAffiliateStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)

        serializer = AffiliateStatusUpdateSerializer(
            affiliate,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0] if serializer.errors else "Invalid data."
            return APIResponse.error(
                message=first_error,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return APIResponse.success(
            message="Affiliate status updated successfully.",
            data={
                "id": affiliate.id,
                "name": affiliate.user.name or affiliate.user.email,
                "email": affiliate.user.email,
                "status": affiliate.status,
            },
            status_code=status.HTTP_200_OK
        )
        
        
# Delete Affiliate View
class DeleteAffiliateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)
        affiliate.delete()

        return APIResponse.success(
            message="Affiliate deleted successfully.",
            data={},
            status_code=status.HTTP_200_OK
        )