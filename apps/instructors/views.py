import calendar
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q,Count,Sum,Avg
from django.utils import timezone
from apps.enrollments.models import Enrollment
from apps.instructors.models import Instructor
from apps.instructors.serializers import *
from apps.payments.models import Commission
from utils.api_response import APIResponse
from utils.paginations import CustomPagination
from apps.courses.models import Course, LiveClass, Review
from utils.permissions import IsInstructor, IsStudent
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncMonth

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
            pending_review_courses=Count("id", filter=Q(status="Draft")),
            
        )
        certificates_issued = Course.objects.filter(enrollments__is_completed=True).distinct().count()
        ratings_people = Review.objects.values("course").annotate(count=Count("id")).count()
        

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
                    "certificates_issued": certificates_issued,
                    "ratings_people": ratings_people,
                    
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



# Instructor Profile View
class InstructorProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        instructor, _ = Instructor.objects.get_or_create(user=request.user)

        serializer = InstructorProfileSerializer(
            instructor,
            context={"request": request}
        )
        return APIResponse.success(
            message="Instructor profile retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def patch(self, request):
        instructor, _ = Instructor.objects.get_or_create(user=request.user)

        serializer = InstructorProfileSerializer(
            instructor,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(
                message="Instructor profile updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            message="Failed to update instructor profile.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        
        
# Instructor Deshboard View
class InstructorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        month_start = today.replace(day=1)
        start_of_week = today - timedelta(days=today.weekday())

        instructor_courses = Course.objects.filter(instructor=user)

        course_created = instructor_courses.count()

        active_courses = instructor_courses.filter(
            status__in=["published", "accepted", "featured"]
        ).count()

        students_enrolled = Enrollment.objects.filter(
            course__instructor=user,
            is_active=True
        ).values("user").distinct().count()

        live_classes = LiveClass.objects.filter(instructor=request.user)
        now = timezone.now()
        past_sessions = live_classes.filter(
            Q(scheduled_date__lt=now.date()) | 
            Q(scheduled_date=now.date(), scheduled_time__lte=now.time())
        ).order_by('-scheduled_date', '-scheduled_time')
        
        upcoming_live_classes_count = past_sessions.count()

        total_earning = Commission.objects.filter(
            user=user
        ).aggregate(
            total=Sum("commission_amount")
        )["total"] or Decimal("0.00")

        average_rating = Review.objects.filter(
            course__instructor=user
        ).aggregate(
            avg=Avg("rating")
        )["avg"] or 0.0

        recent_enrollments = Enrollment.objects.filter(
            course__instructor=user
        ).select_related("user", "course").order_by("-enrolled_at")[:10]

        recent_activity = [
            {
                "id": enrollment.id,
                "student_name": getattr(enrollment.user, "name", "")
                or getattr(enrollment.user, "full_name", "")
                or getattr(enrollment.user, "username", ""),
                "course_title": enrollment.course.title,
                "message": f'{getattr(enrollment.user, "name", "") or getattr(enrollment.user, "full_name", "") or getattr(enrollment.user, "username", "")} purchased your course "{enrollment.course.title}"',
                "created_at": enrollment.enrolled_at,
            }
            for enrollment in recent_enrollments
        ]

        revenue_rows = Commission.objects.filter(
            user=user,
            created_at__date__gte=month_start,
            created_at__date__lte=today
        ).annotate(
            day=TruncDate("created_at")
        ).values("day").annotate(
            total=Sum("commission_amount")
        ).order_by("day")


        # monthly_revenue_chart = [
        #     {
        #         "label": row["day"].strftime("%b %d"),
        #         "amount": row["total"] or Decimal("0.00")
        #     }
        #     for row in revenue_rows
        # ]
        
        
        current_year = today.year

        revenue_rows = Commission.objects.filter(
            user=user,
            created_at__year=current_year
        ).annotate(
            month=TruncMonth("created_at")
        ).values("month").annotate(
            total=Sum("commission_amount")
        ).order_by("month")

        # map বানাও
        revenue_map = {
            row["month"].month: row["total"] or Decimal("0.00")
            for row in revenue_rows
        }

        # 12 মাস generate
        monthly_revenue_chart = []

        for month in range(1, 13):
            monthly_revenue_chart.append({
                "label": calendar.month_abbr[month],  # Jan, Feb, Mar
                "amount": revenue_map.get(month, Decimal("0.00"))
            })

        total_reviews = Review.objects.filter(course__instructor=user).count()

        rating_breakdown = []
        for stars in [5, 4, 3, 2, 1]:
            count = Review.objects.filter(
                course__instructor=user,
                rating__gte=stars,
                rating__lt=stars + 1
            ).count()

            percentage = round((count / total_reviews) * 100, 2) if total_reviews > 0 else 0

            rating_breakdown.append({
                "stars": stars,
                "count": count,
                "percentage": percentage
            })

        week_days = [start_of_week + timedelta(days=i) for i in range(7)]

        enrollment_rows = Enrollment.objects.filter(
            course__instructor=user,
            enrolled_at__date__gte=start_of_week,
            enrolled_at__date__lte=today
        ).annotate(
            day=TruncDate("enrolled_at")
        ).values("day").annotate(
            total=Count("id")
        )

        completion_rows = Enrollment.objects.filter(
            course__instructor=user,
            is_completed=True,
            enrolled_at__date__gte=start_of_week,
            enrolled_at__date__lte=today
        ).annotate(
            day=TruncDate("enrolled_at")
        ).values("day").annotate(
            total=Count("id")
        )

        enrollment_map = {row["day"]: row["total"] for row in enrollment_rows}
        completion_map = {row["day"]: row["total"] for row in completion_rows}

        course_overview_chart = [
            {
                "label": day.strftime("%a"),
                "enrollments": enrollment_map.get(day, 0),
                "completions": completion_map.get(day, 0),
            }
            for day in week_days
        ]

        return APIResponse.success(
            message="Instructor dashboard fetched successfully.",
            data={
                "course_created": course_created,
                "active_courses": active_courses,
                "students_enrolled": students_enrolled,
                "online_sessions": upcoming_live_classes_count,
                "total_earning": total_earning,
                "average_rating": round(float(average_rating), 1) if average_rating else 0.0,
                "recent_activity": recent_activity,
                "monthly_revenue_chart": monthly_revenue_chart,
                "rating_breakdown": rating_breakdown,
                "course_overview_chart": course_overview_chart,
            },
            status_code=status.HTTP_200_OK
        )