from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from apps.enrollments.models import Enrollment
from apps.payments.models import Invoice
from apps.courses.models import  LectureProgress, Course
from .serializers import StudentDashboardSerializer
from utils.api_response import APIResponse

class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        enrollments = Enrollment.objects.filter(user=user)

        enrolled_courses_count = enrollments.count()
        active_courses_count = enrollments.filter(is_active=True, is_completed=False).count()
        completed_courses_count = enrollments.filter(is_completed=True).count()
        recently_enrolled = [
            enrollment.course for enrollment in enrollments.order_by("-enrolled_at")[:4]
        ]

        recent_invoices = Invoice.objects.filter(user=user).order_by("-invoice_date", "-created_at")[:10]

        data = {
            "enrolled_courses_count": enrolled_courses_count,
            "active_courses_count": active_courses_count,
            "completed_courses_count": completed_courses_count,
            "recently_enrolled": recently_enrolled,
            "recent_invoices": recent_invoices,
        }

        serializer = StudentDashboardSerializer(instance=data, context={"request": request})

        return APIResponse.success(
            message="Student dashboard data fetched successfully.",
            data=serializer.data,
            status_code=200
        )



