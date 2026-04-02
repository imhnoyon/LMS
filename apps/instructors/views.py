from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q,Count
from apps.instructors.models import Instructor
from apps.instructors.serializers import *
from utils.api_response import APIResponse
from utils.paginations import CustomPagination

# List pending instructors for admin review
class PendingInstructorListView(APIView):
    permission_classes = [IsAuthenticated,IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search", "").strip()

        
        instructors = Instructor.objects.filter(
             Q(is_approved=False) | Q(is_featured=False)
        ).select_related("user").order_by("-id")
        
        if search:
            instructors = instructors.filter(
                Q(user__email__icontains=search) |
                Q(user__name__icontains=search) |
                Q(user__id__icontains=search)
            )
        paginator = self.pagination_class()
        paginated_instructors = paginator.paginate_queryset(instructors, request, view=self)
        serializer = PendingInstructorListSerializer(paginated_instructors, many=True, context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
            message="Instructors retrieved successfully."
        )
        
        




# Approve an instructor
class ApproveInstructorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        instructor = get_object_or_404(Instructor, pk=pk)

        if instructor.is_approved:
            return APIResponse.error(
                message="Instructor already approved.",
                status_code=400
            )

        instructor.is_approved = True
        instructor.save(update_fields=["is_approved"])

        return APIResponse.success(
            message="Instructor approved successfully.",
            data={
                "id": instructor.id,
                "email": instructor.user.email,
                "is_approved": instructor.is_approved
            },
            status_code=200
        )
        
 # Feature an approved instructor       
class FeatureApprovedInstructorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        instructor = get_object_or_404(Instructor, pk=pk)

        if not instructor.is_approved:
            return APIResponse.error(
                message="Approve instructor before featuring.",
                status_code=400
            )
        if instructor.is_featured:
            return APIResponse.error(
                message="Instructor already featured.",
                status_code=400
            )

        instructor.is_featured = True
        instructor.save(update_fields=["is_featured"])

        return APIResponse.success(
            message="Instructor featured successfully.",
            data={
                "id": instructor.id,
                "email": instructor.user.email,
                "is_approved": instructor.is_featured
            },
            status_code=200
        )
        
# Delete an Instructor  
class DeleteInstructorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        instructor = get_object_or_404(Instructor, pk=pk)
        instructor.delete()

        return APIResponse.success(
            message="Instructor deleted successfully.",
            status_code=200
        )
    
    
class CourseListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search")
        category = request.query_params.get("category")
        status_param = request.query_params.get("status")
        language = request.query_params.get("language")
        level = request.query_params.get("level")

        courses = Course.objects.all().order_by("-id")

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search)
            )

        if category:
            courses = courses.filter(category_id=category)

        if status_param:
            courses = courses.filter(status__iexact=status_param)

        if language:
            courses = courses.filter(language__iexact=language)

        if level:
            courses = courses.filter(level__iexact=level)

        # top summary stats
        all_course_stats = Course.objects.aggregate(
            approved_courses=Count("id", filter=Q(status="Accepted")),
            published_courses=Count("id", filter=Q(status="Published")),
            pending_review_courses=Count("id", filter=Q(status="Draft"))
        )

        paginator = self.pagination_class()
        paginated_courses = paginator.paginate_queryset(courses, request)
        serializer = CourseSerializer(paginated_courses, many=True)

        return APIResponse.success(
            message="Courses fetched successfully.",
            data={
                "stats": {
                    "approved_courses": all_course_stats["approved_courses"],
                    "published_courses": all_course_stats["published_courses"],
                    "pending_review_courses": all_course_stats["pending_review_courses"],
                },
                "total": paginator.page.paginator.count,
                "page": paginator.page.number,
                "page_size": paginator.get_page_size(request),
                "total_pages": paginator.page.paginator.num_pages,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
            status_code=200
        )
