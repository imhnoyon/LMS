import base64
import calendar
from rest_framework.views import APIView, Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q,Count,Sum,Avg
from django.utils import timezone
from apps.enrollments.models import Enrollment
from apps.instructors.models import Instructor
from apps.instructors.serializers import *
from apps.payments.models import Commission, Withdrawal
from utils.api_response import APIResponse
from utils.paginations import CustomPagination
from apps.courses.models import Course, LiveClass, Review
from utils.permissions import IsInstructor, IsStudent
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncMonth
from rest_framework.parsers import MultiPartParser, FormParser
from apps.organizations.serializers import LiveSessionUploaderSerializer

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
        status = request.query_params.get("status")
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

        if status:
            courses = courses.filter(status__iexact=status)

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
        print("Course stats:", all_course_stats)
        
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
            message="Instructor profile retrieved.",
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
        
        

# Instructor Earnings View
class InstructorEarningsView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        total_revenue = Commission.objects.filter(user=user).aggregate( total=Sum("commission_amount"))["total"] or Decimal("0.00")

        total_withdrawals = Withdrawal.objects.filter( user=user, status="completed" ).aggregate( total=Sum("amount"))["total"] or Decimal("0.00")

        today_revenue = Commission.objects.filter(user=user,created_at__date=today).aggregate( total=Sum("commission_amount"))["total"] or Decimal("0.00")
        
        current_balance = total_revenue - total_withdrawals
        
        withdrawals_qs = Withdrawal.objects.filter(user=user).order_by("-requested_at")
        
        # ✅ Daily revenue statistic for current month
         # current month day-wise revenue
        month_start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        month_end = today.replace(day=last_day)

        revenue_rows = Commission.objects.filter(
            user=user,
            created_at__date__range=[month_start, month_end]
        ).annotate(
            day=TruncDate("created_at")
        ).values("day").annotate(
            total=Sum("commission_amount")
        ).order_by("day")

        # safe map
        revenue_map = {
            row["day"].strftime("%Y-%m-%d"): row["total"] or Decimal("0.00")
            for row in revenue_rows
        }

        daily_revenue_chart = []
        for day_num in range(1, last_day + 1):
            current_day = date(today.year, today.month, day_num)
            current_day_str = current_day.strftime("%Y-%m-%d")

            daily_revenue_chart.append({
                "label": current_day.strftime("%b %d"),
                "amount": revenue_map.get(current_day_str, Decimal("0.00"))
            })
        serializer = InstructorEarningsSerializer({
            "total_revenue": total_revenue,
            "total_withdrawals": total_withdrawals,
            "current_balance": current_balance,
            "today_revenue": today_revenue,
            "withdrawals": withdrawals_qs,
            "monthly_revenue_chart": daily_revenue_chart
        })

        return APIResponse.success(
            message="Instructor earnings fetched successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
# Withdrawal Request List
class WithdrawalRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  
    pagination_class = CustomPagination

    def get(self, request):
        withdrawals = Withdrawal.objects.filter(
            status__in=["pending", "completed", "rejected"]
        ).select_related("user").order_by("-requested_at")

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(withdrawals, request)

        serializer = WithdrawalRequestSerializer(paginated_data, many=True)

        return paginator.get_paginated_response(serializer.data)







class InstructorLiveSessionUploadView(APIView):
    permission_classes = [IsAuthenticated ,IsInstructor]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, course_id):
        user = request.user
        course = get_object_or_404(Course, id=course_id)

        if user.role != "instructor":
            return APIResponse.error(
                message="Only instructors can upload videos.",
                status_code=403
            )

        if getattr(course, "instructor_id", None) != user.id:
            return APIResponse.error(
                message="You can only upload videos to your own course.",
                status_code=403
            )

        serializer = LiveSessionUploaderSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return APIResponse.error(
                message="Upload failed.",
                errors=serializer.errors,
                status_code=400
            )

        serializer.save(course=course,course_name=course.title   
        )

        return APIResponse.success(
            message="Video uploaded successfully to your course.",
            data=serializer.data,
            status_code=201
        )
        
        

from django.core.files.base import ContentFile
import uuid     
class SignatureUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.get("signature")

        if not data:
            return Response({"error": "No signature provided"}, status=400)

        signature_file = None

        # Handle both base64 string and file upload
        if isinstance(data, str):
            # base64 encoded string
            try:
                format, imgstr = data.split(";base64,")
                ext = format.split("/")[-1]
                file_name = f"{uuid.uuid4()}.{ext}"
                signature_file = ContentFile(
                    base64.b64decode(imgstr),
                    name=file_name
                )
            except (ValueError, IndexError):
                return Response({"error": "Invalid base64 format"}, status=400)
        else:
            # Direct file upload (InMemoryUploadedFile or similar)
            signature_file = data

        if not signature_file:
            return APIResponse.error({"error": "Failed to process signature"}, status_code=400)

        obj, created = Instructor.objects.update_or_create(
            user=request.user,
            defaults={'signature': signature_file}
        )

        return APIResponse.success({
            "message": "Signature saved successfully" if created else "Signature updated successfully",
            "id": obj.id
        })
        
    def patch(self, request):
        data = request.data.get("signature")

        if not data:
            return Response({"error": "No signature provided"}, status=400)

        signature_file = None

        # Handle both base64 string and file upload
        if isinstance(data, str):
            # base64 encoded string
            try:
                format, imgstr = data.split(";base64,")
                ext = format.split("/")[-1]
                file_name = f"{uuid.uuid4()}.{ext}"
                signature_file = ContentFile(
                    base64.b64decode(imgstr),
                    name=file_name
                )
            except (ValueError, IndexError):
                return Response({"error": "Invalid base64 format"}, status=400)
        else:
            # Direct file upload (InMemoryUploadedFile or similar)
            signature_file = data

        if not signature_file:
            return APIResponse.error({"error": "Failed to process signature"}, status_code=400)

        obj, created = Instructor.objects.update_or_create(
            user=request.user,
            defaults={'signature': signature_file}
        )

        return APIResponse.success({
            "message": "Signature saved successfully" if created else "Signature updated successfully",
            "id": obj.id
        })
        
        
class MyInstructorSignatureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        instructor = Instructor.objects.select_related('user').get(user=request.user)
        serializer = InstructorSignatureSerializer(instructor, context={"request": request})

        return Response({
            "success": True,
            "message": "Instructor signature retrieved successfully.",
            "data": serializer.data
        }, status=200)


class InstructorCertificateListView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]
    pagination_class = CustomPagination

    def get(self, request):
        accepted_courses = Course.objects.filter(
            instructor=request.user,
            status="accepted"
        ).order_by("-id")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(accepted_courses, request)

        serializer = InstructorCertificateSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(
            data=serializer.data,
            message="Instructor accepted courses retrieved successfully."
        )
        
        
        
class MyInstructorProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        instructor = get_object_or_404(
            Instructor.objects.select_related('user').prefetch_related('user__courses', 'user__courses__reviews', 'user__courses__reviews__user'),
            user=request.user
        )
        serializer = InstructorProfileDetailSerializer(instructor,context={'request': request})
        return APIResponse.success(message="Instructor profile retrieved successfully.", data=serializer.data)
    

# Instructor List API for public listing
class InstructorListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request,):
        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip().upper()
        include_top_param = request.query_params.get("include_top", "").strip().lower() in ("1", "true", "yes")

        instructors = Instructor.objects.select_related("user").all()[:20]

        if search:
            instructors = instructors.filter(
                Q(user__name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(id__icontains=search) |
                Q(title__icontains=search)
            )

        if status_param:
            if status_param == "ACTIVE":
                instructors = instructors.filter(is_approved=True, user__is_active=True)
            elif status_param == "PENDING":
                instructors = instructors.filter(is_approved=False, user__is_active=True)
            elif status_param == "SUSPENDED":
                instructors = instructors.filter(user__is_active=False)

        serializer = InstructorProfileListSerializer(instructors, many=True, context={"request": request})

        # show top performers by default when user is not searching or filtering
        include_top = include_top_param or (not search and not status_param)

        # If frontend requests top performers, compute top 5 earners (by Commission)
        if include_top:
            from apps.payments.models import Commission
            from django.db.models import Sum, Count

            # Restrict commissions to users who are instructors
            instructor_user_ids = Instructor.objects.values_list('user', flat=True)

            top_qs = (
                Commission.objects
                .filter(user__in=instructor_user_ids)
                .values('user')
                .annotate(total_earned=Sum('commission_amount'), sales_count=Count('id'))
                .order_by('-total_earned')[:5]
            )

            top_performers = []
            for idx, item in enumerate(top_qs, start=1):
                uid = item.get('user')
                total = item.get('total_earned') or 0
                sales = item.get('sales_count') or 0
                user_obj = None
                try:
                    from apps.users.models import User as UserModel
                    user_obj = UserModel.objects.filter(id=uid).first()
                except Exception:
                    user_obj = None

                name = user_obj.name if user_obj and getattr(user_obj, 'name', None) else (user_obj.email if user_obj else None)
                avatar = None
                if user_obj and getattr(user_obj, 'avatar', None):
                    req = request
                    try:
                        avatar = req.build_absolute_uri(user_obj.avatar.url) if req else user_obj.avatar.url
                    except Exception:
                        avatar = user_obj.avatar.url

                # try to include instructor code/id
                instr = Instructor.objects.filter(user_id=uid).first()
                code = instr.id if instr else None

                top_performers.append({
                    'rank': idx,
                    'user_id': uid,
                    'name': name,
                    'avatar': avatar,
                    'code': code,
                    'total_earned': format(total, '.2f'),
                    'sales_count': sales,
                })

            return APIResponse.success(
                message="Instructors retrieved successfully.",
                data={
                    'top_performers': top_performers,
                    'instructors': serializer.data,
                }
            )

        return APIResponse.success(message="Instructors retrieved successfully.", data=serializer.data)
    
    
    
class AdminInstructorDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        instructor = get_object_or_404(
            Instructor.objects.select_related('user').prefetch_related('user__courses', 'user__courses__reviews', 'user__courses__reviews__user'),
            id=pk
        )
        serializer = InstructorProfileDetailSerializer(instructor, context={'request': request})
        return APIResponse.success(message="Instructor profile retrieved successfully.", data=serializer.data)
    
    
    
    
class AdminInstructorListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination
    def get(self, request,):
        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip().upper()

        instructors = Instructor.objects.select_related("user").all()

        if search:
            instructors = instructors.filter(
                Q(user__name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(id__icontains=search) |
                Q(title__icontains=search)
            )

        if status_param:
            if status_param == "ACTIVE":
                instructors = instructors.filter(is_approved=True, user__is_active=True)
            elif status_param == "PENDING":
                instructors = instructors.filter(is_approved=False, user__is_active=True)
            elif status_param == "SUSPENDED":
                instructors = instructors.filter(user__is_active=False)

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(
            instructors,
            request
        )

        serializer = AdminInstructorProfileListSerializer(
            paginated_queryset,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(
            serializer.data,
            message="Instructors retrieved successfully."
        )
        