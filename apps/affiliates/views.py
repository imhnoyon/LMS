from rest_framework.views import APIView, settings
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from django.db.models import Q
from apps.courses.models import Course

from .models import Affiliate, AffiliateCourseLink
from .serializers import AffiliateCourseListSerializer, AffiliateListSerializer
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
        
        
        


# Affiliate course list view for affiliate users
class AffiliateCourseListView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination

    def get(self, request):
        if request.user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can access this course list.",
                status_code=403
            )

        search = request.query_params.get("search")
        category = request.query_params.get("category")

        courses = Course.objects.select_related("category", "advance_info").filter(
            status="accepted"
        ).order_by("-created_at")

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search)
            )

        if category:
            courses = courses.filter(category_id=category)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = AffiliateCourseListSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)
        
        
# Generate course referral link for affiliate users
class GenerateAffiliateCourseLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        user = request.user

        if user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can generate referral links.",
                status_code=403
            )

        affiliate = get_object_or_404(Affiliate, user=user)
        course = get_object_or_404(Course, id=course_id, status="accepted")

        link, created = AffiliateCourseLink.objects.get_or_create(
            affiliate=affiliate,
            course=course
        )

        # Dynamically grab the frontend's exact URL (whether localhost or production)
        base_frontend_url = request.headers.get("Origin")
        if not base_frontend_url:
            base_frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8002")
            
        frontend_url = f"{base_frontend_url}/course/{course.id}?ref={link.code}"

        if link.referral_url != frontend_url:
            link.referral_url = frontend_url
            link.save(update_fields=["referral_url"])

        return APIResponse.success(
            message="Affiliate course link generated successfully.",
            data={
                "course_id": course.id,
                "course_title": course.title,
                "referral_code": link.code,
                "referral_url": link.referral_url
            },
            status_code=200
        )