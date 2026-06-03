import calendar

from rest_framework.views import APIView, Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from apps.courses.models import Course, LiveClass, Review
from apps.courses.serializers import CourseDetailSerializer, LiveClassSerializer
from apps.enrollments.models import Enrollment
from apps.payments.models import Commission, Payment, Withdrawal
from utils.permissions import IsInstructor, IsOrganization
from .models import Organization, Membership, Invitation
from .serializers import *
from utils.paginations import CustomPagination
from utils.api_response import APIResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from django.db.models import Q, Avg, Count, Sum
from apps.users.models import User
from utils.emails import send_invitation_email
from decimal import Decimal
from django.db.models.functions import TruncDate, TruncMonth
from datetime import date, timedelta
from django.utils.dateparse import parse_date


# View to list unverified organizations for admin review
class UnverifiedOrganizationListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search", "")
        organizations = Organization.objects.filter(
            is_verified=False
        ).order_by("-created_at")

        if search:
            organizations = organizations.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(id__icontains=search) |
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

# 🚀 View to invite a member/instructor to organization
class InviteInstructorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        membership = Membership.objects.filter(user=request.user, role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]).first()

        if not membership:
            return APIResponse.error(
                message="You don't have permission to invite members to any organization.", 
                status_code=403
            )

        organization = membership.organization

        serializer = InvitationSerializer(data=request.data, context={'organization': organization})
        if not serializer.is_valid():
            return APIResponse.error(
                message="Invalid invitation data.", 
                errors=serializer.errors, 
                status_code=400
            )

        email = serializer.validated_data['email'].lower()
        user_exists = User.objects.filter(email=email).exists()

        invitation = serializer.save(organization=organization, invited_by=request.user)
        
        # Send Email via helper
        send_invitation_email(
            email=email,
            organization_name=organization.name,
            invitation_token=str(invitation.token),
            is_registered=user_exists
        )

        return APIResponse.success(
            message=f"Invitation to join '{organization.name}' sent successfully.",
            data=serializer.data,
            status_code=201
        )

# 🗃️ View to get invitation details (for frontend display)
class InvitationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)
        
        if invitation.status != Invitation.Status.PENDING:
            return APIResponse.error(message="This invitation is no longer active.", status_code=400)
            
        if invitation.is_expired():
            invitation.status = Invitation.Status.EXPIRED
            invitation.save()
            return APIResponse.error(message="This invitation has expired.", status_code=400)
            
        return APIResponse.success(
            message="Invitation details retrieved.",
            data={
                "id": invitation.id,
                "organization": invitation.organization.name,
                "invited_by": invitation.invited_by.name or invitation.invited_by.email,
                "email": invitation.email,
                "role": invitation.role,
                "created_at": invitation.created_at
            }
        )

# ✅ View to accept or reject an invitation
class RespondInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)
        action = request.data.get('action') 

        if invitation.status != Invitation.Status.PENDING:
            return APIResponse.error(message="This invitation has already been processed.", status_code=400)

        if invitation.is_expired():
             invitation.status = Invitation.Status.EXPIRED
             invitation.save()
             return APIResponse.error(message="This invitation has expired.", status_code=400)

        if invitation.email.lower() != request.user.email.lower():
             return APIResponse.error(
                 message=f"You are logged in as {request.user.email}, but this invitation was sent to {invitation.email}.", 
                 status_code=403
             )

        if action == 'accept':
            invitation.status = Invitation.Status.ACCEPTED
            invitation.save()
            
            # Assign Membership
            Membership.objects.get_or_create(
                organization=invitation.organization,
                user=request.user,
                defaults={'role': invitation.role, 'status': Membership.Status.ACTIVE}
            )

            # Ensure user has correct platform role and instructor profile update
            if invitation.role == Membership.Role.INSTRUCTOR:
                if request.user.role != 'instructor':
                    request.user.role = 'instructor'
                    request.user.save(update_fields=['role'])
                
                #  Update Instructor model flag
                from apps.instructors.models import Instructor
                instructor, _ = Instructor.objects.get_or_create(user=request.user)
                instructor.is_organization_instructor = True
                instructor.save(update_fields=['is_organization_instructor'])

            return APIResponse.success(message=f"Welcome! You are now a {invitation.role} at {invitation.organization.name}.")
        
        elif action == 'reject':
            invitation.status = Invitation.Status.REJECTED
            invitation.save()
            return APIResponse.success(message="Invitation rejected successfully.")

        else:
            return APIResponse.error(message="Invalid action. Use 'accept' or 'reject'.", status_code=400)
        
        
        
 # View for organization instructors to see their dashboard with members and stats       
class OrganizationInstructorDashboardView(APIView):
    permission_classes = [IsAuthenticated,IsOrganization]

    def get_user_organization(self, user):
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get(self, request):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to access this organization dashboard.",
                status_code=403
            )

        organization = org_membership.organization

        search = request.query_params.get("search")
        role = request.query_params.get("role")
        status_param = request.query_params.get("status")

        memberships = Membership.objects.filter(
            organization=organization,
            role=Membership.Role.INSTRUCTOR
        ).select_related("user", "organization").order_by("-joined_at")

        if search:
            memberships = memberships.filter(
                Q(user__name__icontains=search) |
                Q(user__email__icontains=search)
            )

        if role:
            memberships = memberships.filter(role=role)

        if status_param:
            memberships = memberships.filter(status=status_param)

        serializer = OrganizationMembershipSerializer(
            memberships,
            many=True,
            context={"request": request}
        )

        total_instructors = Membership.objects.filter(
            organization=organization,
            role=Membership.Role.INSTRUCTOR
        ).count()

        active_instructors = Membership.objects.filter(
            organization=organization,
            role=Membership.Role.INSTRUCTOR,
            status=Membership.Status.ACTIVE
        ).count()

        pending_invitations = Invitation.objects.filter(
            organization=organization,
            role=Membership.Role.INSTRUCTOR,
            status=Invitation.Status.PENDING
        ).count()

        
        org_courses = Course.objects.filter(organization=organization)
        active_courses = org_courses.filter(
            status__in=[ "accepted", "featured"]
        ).count()

        return APIResponse.success(
            message="Organization instructor dashboard fetched successfully.",
            data={
                "stats": {
                    "total_instructors": total_instructors,
                    "active_instructors": active_instructors,
                    "pending_invitations": pending_invitations,
                    "total_courses": active_courses,
                },
                "memberships list": serializer.data,
            },
            status_code=200
        )
        

class InstructorOrganizationListAPIView(APIView):
    """Returns list of organizations where the logged-in user is an instructor (membership-based)."""
    permission_classes = [IsAuthenticated, IsInstructor]

    def get(self, request):
        # Fetch memberships where the user is an instructor
        memberships = Membership.objects.filter(
            user=request.user,
            role=Membership.Role.INSTRUCTOR,
            status=Membership.Status.ACTIVE
        ).select_related("organization").order_by("-joined_at")

        serializer = InstructorOrganizationSerializer(memberships, many=True, context={"request": request})

        return APIResponse.success(
            message="Instructor organizations retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
        


# ── Instructor Live Class Stats 
class InstructorOrganizationLiveClassStatsView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    def get(self, request):
        from django.utils import timezone
        now = timezone.now()
        user = request.user
        instructor = getattr(user, 'instructor', None)
        
        # ✅ Check exists on Instructor model, not User model directly
        is_org_inst = instructor and instructor.is_organization_instructor
        
        if is_org_inst:
             membership = Membership.objects.filter(
                 user=user,
                 role=Membership.Role.INSTRUCTOR,
                 status=Membership.Status.ACTIVE
             ).first()
             
             if membership:
                 live_classes = LiveClass.objects.filter(course__organization=membership.organization)
             else:
                 live_classes = LiveClass.objects.none()
        else:
            # ✅ Ensure live_classes is defined for non-org instructors
            live_classes = LiveClass.objects.filter(instructor=user)
        
        
        total_live_classes = live_classes.count()
        
        upcoming_sessions = live_classes.filter(
            Q(scheduled_date__gt=now.date()) | 
            Q(scheduled_date=now.date(), scheduled_time__gt=now.time())
        ).order_by('scheduled_date', 'scheduled_time')
        
        past_sessions = live_classes.filter(
            Q(scheduled_date__lt=now.date()) | 
            Q(scheduled_date=now.date(), scheduled_time__lte=now.time())
        ).order_by('-scheduled_date', '-scheduled_time')
        
        upcoming_live_classes_count = upcoming_sessions.count()
        
        from apps.enrollments.models import Enrollment
        if is_org_inst:
             students_enrolled = Enrollment.objects.filter(
                course__organization=membership.organization if membership else None, 
                is_active=True
            ).values('user').distinct().count()
        else:
            students_enrolled = Enrollment.objects.filter(
                course__instructor=user, 
                is_active=True
            ).values('user').distinct().count()

        upcoming_serialized = LiveClassSerializer(upcoming_sessions, many=True).data
        past_serialized = LiveClassSerializer(past_sessions, many=True).data

        return APIResponse.success(
            data={
                "total_live_classes": total_live_classes,
                "upcoming_live_classes_count": upcoming_live_classes_count,
                "students_enrolled": students_enrolled,
                "upcoming_sessions": upcoming_serialized,
                "past_sessions": past_serialized
            }
        )

        

class LiveClassOrganizationInstructorManageView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]
    pagination_class = CustomPagination

    def post(self, request, course_id):
        user = request.user
        instructor = getattr(user, 'instructor', None)

        #  Check if the user is a verified Organization Instructor
        if not instructor or not instructor.is_organization_instructor:
            return APIResponse.error(
                message="Access denied. Only organization-affiliated instructors can schedule these live classes.",
                status_code=403
            )

        #  Get the instructor's organization
        membership = Membership.objects.filter(user=user, role=Membership.Role.INSTRUCTOR, status=Membership.Status.ACTIVE).first()

        if not membership:
            return APIResponse.error(message="No active organization membership found.", status_code=403)

        #  Verify the course actually belongs to the instructor's organization
        course = get_object_or_404(Course, pk=course_id, organization=membership.organization)

        serializer = LiveClassSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course, instructor=user)
            return APIResponse.success(
                message="Organization live class scheduled successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)




class OrganizationLiveSessionUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, course_id):
        user = request.user
        course = get_object_or_404(Course, id=course_id)

        # only instructor
        if user.role != "instructor":
            return APIResponse.error(
                message="Only instructors can upload videos.",
                status_code=403
            )

        # must be organization instructor
        instructor = getattr(user, "instructor", None)
        if not instructor or not instructor.is_organization_instructor:
            return APIResponse.error(
                message="You are not an organization instructor.",
                status_code=403
            )

        # check membership + same organization
        is_org_instructor = Membership.objects.filter(
            user=user,
            organization_id=getattr(course, "organization_id", None),
            role=Membership.Role.INSTRUCTOR,
            status=Membership.Status.ACTIVE
        ).exists()

        if not is_org_instructor:
            return APIResponse.error(
                message="You are not assigned to this organization's course.",
                status_code=403
            )

        serializer = LiveSessionUploaderSerializer(data=request.data, context={"request": request})

        if not serializer.is_valid():
            return APIResponse.error(
                message="Upload failed.",
                errors=serializer.errors,
                status_code=400
            )

        serializer.save(course=course, course_name=course.title)

        return APIResponse.success(
            message="Video uploaded to organization course successfully.",
            data=serializer.data,
            status_code=201
        )

class OrganizationDashboardView(APIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        user = request.user

        #  get organization (admin/manager only)
        membership = Membership.objects.filter(
            user=user,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER, Membership.Role.INSTRUCTOR],
            status=Membership.Status.ACTIVE
        ).select_related("organization").first()

        if not membership:
            return APIResponse.error(
                message="You are not authorized for any organization.",
                status_code=403
            )

        organization = membership.organization

        today = timezone.localdate()
        month_start = today.replace(day=1)
        start_of_week = today - timedelta(days=today.weekday())

        org_courses = Course.objects.filter(organization=organization)

        # 📊 Course stats
        course_created = org_courses.count()

        active_courses = org_courses.filter(
            status__in=[ "accepted", "featured"]
        ).count()

        students_enrolled = Enrollment.objects.filter(
            course__organization=organization,
            is_active=True
        ).values("user").distinct().count()

        # 🎥 Live classes
        live_classes = LiveClass.objects.filter(course__organization=organization)
        now = timezone.now()

        past_sessions = live_classes.filter(
            Q(scheduled_date__lt=now.date()) |
            Q(scheduled_date=now.date(), scheduled_time__lte=now.time())
        )

        upcoming_live_classes_count = past_sessions.count()

        # 💰 Earnings (FULL org revenue)
        total_earning = Commission.objects.filter(
            course__organization=organization
        ).aggregate(
            total=Sum("commission_amount")
        )["total"] or Decimal("0.00")

        # ⭐ Rating
        average_rating = Review.objects.filter(
            course__organization=organization
        ).aggregate(
            avg=Avg("rating")
        )["avg"] or 0.0

        #  Recent Activity
        recent_enrollments = Enrollment.objects.filter(
            course__organization=organization
        ).select_related("user", "course").order_by("-enrolled_at")[:10]

        recent_activity = [
            {
                "id": e.id,
                "student_name": getattr(e.user, "name", "") or getattr(e.user, "username", ""),
                "course_title": e.course.title,
                "message": f'{getattr(e.user, "name", "") or getattr(e.user, "username", "")} purchased "{e.course.title}"',
                "created_at": e.enrolled_at,
            }
            for e in recent_enrollments
        ]

        # 📈 Monthly Revenue Chart
        current_year = today.year

        revenue_rows = Commission.objects.filter(
            course__organization=organization,
            created_at__year=current_year
        ).annotate(
            month=TruncMonth("created_at")
        ).values("month").annotate(
            total=Sum("commission_amount")
        )

        revenue_map = {
            row["month"].month: row["total"] or Decimal("0.00")
            for row in revenue_rows
        }

        monthly_revenue_chart = [
            {
                "label": calendar.month_abbr[m],
                "amount": revenue_map.get(m, Decimal("0.00"))
            }
            for m in range(1, 13)
        ]

        #  Rating Breakdown
        total_reviews = Review.objects.filter(
            course__organization=organization
        ).count()

        rating_breakdown = []
        for stars in [5, 4, 3, 2, 1]:
            count = Review.objects.filter(
                course__organization=organization,
                rating__gte=stars,
                rating__lt=stars + 1
            ).count()

            percentage = round((count / total_reviews) * 100, 2) if total_reviews > 0 else 0

            rating_breakdown.append({
                "stars": stars,
                "count": count,
                "percentage": percentage
            })

        # 📊 Weekly Course Overview
        week_days = [start_of_week + timedelta(days=i) for i in range(7)]

        enrollment_rows = Enrollment.objects.filter(
            course__organization=organization,
            enrolled_at__date__gte=start_of_week,
            enrolled_at__date__lte=today
        ).annotate(
            day=TruncDate("enrolled_at")
        ).values("day").annotate(total=Count("id"))

        completion_rows = Enrollment.objects.filter(
            course__organization=organization,
            is_completed=True,
            enrolled_at__date__gte=start_of_week,
            enrolled_at__date__lte=today
        ).annotate(
            day=TruncDate("enrolled_at")
        ).values("day").annotate(total=Count("id"))

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
            message="Organization dashboard fetched successfully.",
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
            status_code=200
        )
    
    
 # Course list Seen by Organization Instructor (only org courses, with search and filter)
class CourseListByOrganizationView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination

    def get(self, request):
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        category_id = request.query_params.get('category_id') or request.query_params.get('categoryId')
        status_param = request.query_params.get('status')

        membership = Membership.objects.filter(user=request.user, status=Membership.Status.ACTIVE).first()
        if not membership:
            courses = Course.objects.none()
        else:
            courses = Course.objects.filter(organization=membership.organization,status="accepted").order_by('-id')
        

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search) |
                Q(language__icontains=search) |
                Q(level__icontains=search)
            )

        # Allow filtering directly by numeric category id via `category_id` (preferred)
        if category_id:
            cid = category_id.strip()
            if cid.isdigit():
                courses = courses.filter(category_id=int(cid))
        elif category:
            # Support filtering by category name (exact or partial), slug, or numeric id
            cat = category.strip()
            if cat.isdigit():
                courses = courses.filter(category_id=int(cat))
            else:
                courses = courses.filter(
                    Q(category__name__iexact=cat) |
                    Q(category__slug__iexact=cat) |
                    Q(category__name__icontains=cat)
                )
        if status_param:
            courses = courses.filter(status__iexact=status_param)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = CourseDetailSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)   

        
class OrganizationEarningsDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    def get_user_organization(self, user):
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get(self, request):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to access this organization dashboard.",
                status_code=403
            )

        organization = org_membership.organization

        total_revenue = Commission.objects.filter(user=org_membership.user).aggregate( total=Sum("commission_amount"))["total"] or Decimal("0.00")
        
        # pending_earnings = organization.pending_earnings
        # available_earnings = organization.available_earnings

        return APIResponse.success(
            message="Organization earnings dashboard fetched successfully.",
            data={
                "total_revenue": total_revenue,
                # "pending_earnings": pending_earnings,
                # "available_earnings": available_earnings,
            },
            status_code=200
        )
        
        
        
        
class OrganizationAdminListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip().upper()

        organizations = Organization.objects.prefetch_related(
            "memberships__user"
        ).all()

        if search:
            organizations = organizations.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(memberships__role=Membership.Role.ADMIN, memberships__user__name__icontains=search) |
                Q(memberships__role=Membership.Role.ADMIN, memberships__user__email__icontains=search)
            ).distinct()

        if status_param:
            if status_param == "ACTIVE":
                organizations = organizations.filter(is_active=True)

            elif status_param == "INACTIVE":
                organizations = organizations.filter(is_active=False)

            elif status_param == "VERIFIED":
                organizations = organizations.filter(is_verified=True)

            elif status_param == "UNVERIFIED":
                organizations = organizations.filter(is_verified=False)

        paginator = self.pagination_class()

        paginated_queryset = paginator.paginate_queryset(
            organizations,
            request
        )

        serializer = OrganizationAdminSerializer(
            paginated_queryset,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(
            serializer.data,
            message="Organizations retrieved successfully."
        )
        
        
class OrganizationAdminDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)

        serializer = OrganizationAdminSerializer(
            organization,
            context={"request": request}
        )

        return APIResponse.success(
            message="Organization details retrieved successfully.",
            data=serializer.data,
            status_code=200
        )
        
        

# View for organization  to see their earnings, withdrawals, and revenue stats        
class OrganizationEarningsView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        total_revenue = Commission.objects.filter(user=user).aggregate( total=Sum("commission_amount"))["total"] or Decimal("0.00")

        total_withdrawals = Withdrawal.objects.filter( user=user, status="completed" ).aggregate( total=Sum("amount"))["total"] or Decimal("0.00")

        today_revenue = Commission.objects.filter(user=user,created_at__date=today).aggregate( total=Sum("commission_amount"))["total"] or Decimal("0.00")
        
        current_balance = total_revenue - total_withdrawals
        
        withdrawals_qs = Withdrawal.objects.filter(user=user).order_by("-requested_at")
        
        #  Daily revenue statistic for current month
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
        serializer = OrganizationEarningsSerializer({
            "total_revenue": total_revenue,
            "total_withdrawals": total_withdrawals,
            "current_balance": current_balance,
            "today_revenue": today_revenue,
            "withdrawals": withdrawals_qs,
            "monthly_revenue_chart": daily_revenue_chart
        })

        return APIResponse.success(
            message="Organization earnings fetched successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
# View to toggle membership status (active/suspend) for organization admins       
class ToggleMembershipStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            membership = Membership.objects.select_related("user").get(id=pk)
        except Membership.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Membership not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Toggle status
        if membership.status == "active":
            membership.status = "suspend"
            message = "User suspended successfully"
        else:
            membership.status = "active"
            message = "User activated successfully"

        membership.save()

        return Response(
            {
                "success": True,
                "message": message,
                "data": {
                    "membership_id": membership.id,
                    "user_id": membership.user.id,
                    "user_name": membership.user.name,
                    "status": membership.status,
                }
            },
            status=status.HTTP_200_OK
        )
        
        
class OrInstructorListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]
    pagination_class = CustomPagination

    def get_user_organization(self, user):
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get(self, request):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to access this organization's instructors.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        organization = org_membership.organization
        search = request.query_params.get("search", "")
        status_param = request.query_params.get("status", "")

        # Filter memberships for instructors in this organization
        memberships = Membership.objects.filter(
            organization=organization,
            role=Membership.Role.INSTRUCTOR
        ).select_related("user", "organization").order_by("-joined_at")

        if search:
            memberships = memberships.filter(
                Q(user__name__icontains=search) |
                Q(user__email__icontains=search)
            )

        if status_param:
            memberships = memberships.filter(status=status_param)

        paginator = self.pagination_class()
        paginated_memberships = paginator.paginate_queryset(memberships, request, view=self)
        serializer = OrInstructorSerializer(paginated_memberships, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="Organization instructors retrieved successfully."
        )
        
        
        
class MyOrganizationCourseListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]
    pagination_class = CustomPagination

    def get(self, request):
        # Get user's organization membership
        membership = Membership.objects.filter(
            user=request.user,
            status=Membership.Status.ACTIVE
        ).select_related("organization").first()

        if not membership:
            return APIResponse.error(
                message="You do not have an active organization membership.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        organization = membership.organization
        search = request.query_params.get("search", "")
        status_param = request.query_params.get("status", "")

        # Filter courses by the user's organization
        courses = Course.objects.filter(
            organization=organization
        ).select_related("organization").order_by("-id")

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search)
            )

        if status_param:
            courses = courses.filter(status__iexact=status_param)

        paginator = self.pagination_class()
        paginated_courses = paginator.paginate_queryset(courses, request, view=self)
        serializer = OrCourseSerializer(paginated_courses, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="Organization courses retrieved successfully."
        )
        
        
class OrganizationMemberAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    def get_user_organization(self, user):
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get(self, request):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to access this organization's member analytics.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        organization = org_membership.organization

        # Get all members
        all_members = Membership.objects.filter(organization=organization,).exclude(role=Membership.Role.ADMIN).select_related("user")

        # Count by status
        total_members = all_members.count()
        active_members = all_members.filter(status=Membership.Status.ACTIVE).count()
        suspended_members = all_members.filter(status=Membership.Status.SUSPENDED).count()
        # Active members by role
        return APIResponse.success(
            message="Organization member analytics retrieved successfully.",
            data={
                "summary": {
                    "total_members": total_members,
                    "active_members": active_members,
                    "suspended_members": suspended_members,
                },
            },
            status_code=status.HTTP_200_OK
        )
        
        
class ContractListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]
    pagination_class = CustomPagination

    def get_user_organization(self, user):
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get(self, request):
        org_membership = self.get_user_organization(request.user)
        search = request.query_params.get("search", "")
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to access contracts for this organization.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        contracts = Contract.objects.filter(
            organization=org_membership.organization
        ).select_related("organization", "instructor__user", "course").order_by("-created_at")

        if search:
            contracts = contracts.filter(
                Q(instructor__user__name__icontains=search) |
                Q(course__title__icontains=search)
            )

        paginator = self.pagination_class()
        paginated_contracts = paginator.paginate_queryset(contracts, request, view=self)
        serializer = ContractSerializer(paginated_contracts, many=True, context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
            message="Contracts retrieved successfully."
        )


    def post(self, request):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to create contracts for this organization.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = ContractCreateSerializer(
            data=request.data,
            context={"organization": org_membership.organization}
        )

        if not serializer.is_valid():
            return APIResponse.error(
                message="Invalid contract data.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        contract = serializer.save()
        response_serializer = ContractSerializer(contract)

        return APIResponse.success(
            message="Contract created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )
        
        
    def patch(self, request, contract_id):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to update contracts for this organization.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            contract = Contract.objects.select_related("organization").get(id=contract_id, organization=org_membership.organization)
        except Contract.DoesNotExist:
            return APIResponse.error(
                message="Contract not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Only allow updating revenue_share and expiry_date for now
        revenue_share = request.data.get("revenue_share")
        expiry_date = request.data.get("expiry_date")

        if revenue_share is not None:
            if not (0 <= float(revenue_share) <= 100):
                return APIResponse.error(
                    message="Revenue share must be between 0 and 100 (0-100%).",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            contract.revenue_share = revenue_share

        if expiry_date is not None:
            contract.expiry_date = parse_date(expiry_date) if isinstance(expiry_date, str) else expiry_date

        contract.save()
        response_serializer = ContractSerializer(contract)

        return APIResponse.success(
            message="Contract updated successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
        )
        
 
 
class ContractDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    def get_user_organization(self, user):
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get(self, request, contract_id):
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return APIResponse.error(
                message="You do not have permission to access this contract.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            contract = Contract.objects.select_related("organization", "instructor__user", "course").get(id=contract_id, organization=org_membership.organization)
        except Contract.DoesNotExist:
            return APIResponse.error(
                message="Contract not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ContractSerializer(contract,context={"request": request})

        return APIResponse.success(
            message="Contract details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class OrganizationProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    # Get Organization Profile
    def get(self, request):
        try:
            # Get user's organization via Membership (admin/manager role)
            membership = Membership.objects.filter(
                user=request.user,
                role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER],
                status=Membership.Status.ACTIVE
            ).select_related('organization').first()
            
            if not membership:
                return APIResponse.error(
                    message="Organization not found or you don't have admin access.",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            organization = membership.organization
        except Organization.DoesNotExist:
            return APIResponse.error(
                message="Organization not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = OrganizationProfileSerializer(organization, context={"request": request})

        return APIResponse.success(
            message="Organization profile retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    # Update Organization Profile
    def patch(self, request):
        try:
            # Get user's organization via Membership (admin/manager role)
            membership = Membership.objects.filter(
                user=request.user,
                role__in=[Membership.Role.ADMIN],
                status=Membership.Status.ACTIVE
            ).select_related('organization').first()
            
            if not membership:
                return APIResponse.error(
                    message="Organization not found or you don't have admin access.",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            organization = membership.organization
        except Organization.DoesNotExist:
            return APIResponse.error(
                message="Organization not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = OrganizationProfileSerializer(
            organization,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return APIResponse.success(
                message="Organization profile updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            message="Validation failed.",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        
        
        

class OrganizationProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        membership = Membership.objects.filter(
            user=user,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
        ).select_related("organization").first()

        if not membership or not getattr(membership, 'organization', None):
            raise Http404("Organization not found for this user.")

        return membership.organization

    # Retrieve Organization Information
    def get(self, request):
        organization = self.get_object()
        serializer = OrganizationProfileSerializer(organization, context={"request": request})
        return APIResponse.success(
            message="Organization information retrieved successfully.",
            data=serializer.data
        )

    # Update Organization Information
    def patch(self, request):
        organization = self.get_object()
        serializer = OrganizationProfileSerializer(organization,data=request.data,partial=True,context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(
                message="Organization information updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return APIResponse.error(
            message="Validation error.",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        
        
class InstructorContractCourseListView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        category = request.query_params.get("category", "").strip()
        
        # Logged in instructor membership
        instructor_memberships = Membership.objects.filter(user=request.user)
        
        if search:
            instructor_memberships = instructor_memberships.filter(
                Q(organization__courses__title__icontains=search) 
                
            )
        
        if category:
            instructor_memberships = instructor_memberships.filter(
                Q(organization__courses__category__name__icontains=category)
            )

        contracts = Contract.objects.filter(instructor__in=instructor_memberships).select_related("course","organization","instructor",).order_by("-created_at")
        paginator=self.paginator_class()
        paginated_contracts=paginator.paginate_queryset(contracts,request,view=self)
        serializer = InstructorContractCourseSerializer(
            paginated_contracts,
            many=True,
            context={"request": request}
        )

        return  paginator.get_paginated_response(
            data=serializer.data,
            message="Course review list retrieved successfully"
        )
        
        
        
class InstructorContractCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
       
        # Logged in instructor membership
        instructor_memberships = Membership.objects.filter(user=request.user)
        
        contracts = Contract.objects.filter(instructor__in=instructor_memberships).select_related("course","organization","instructor",).order_by("-created_at")
        serializer = InstructorContractCategorySerializer(
            contracts,
            many=True
        )

        return APIResponse.success(
            message="Instructor contract category list retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class InstructorEarningsChartAPIView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    def get(self, request):
        instructor_memberships = Membership.objects.filter(
            user=request.user,
            role=Membership.Role.INSTRUCTOR,
            status=Membership.Status.ACTIVE,
        ).select_related("organization")

        contracts = Contract.objects.filter(
            instructor__in=instructor_memberships
        ).select_related(
            "course",
            "organization",
            "instructor__user",
        ).order_by("-created_at")

        assigned_course_list = []
        total_earning_amount = Decimal("0.00")

        for contract in contracts:
            discount_price = contract.course.discount_price or Decimal("0.00")
            assigned_percentage = Decimal(str(contract.revenue_share or 0))
            calculated_earning = (discount_price * assigned_percentage) / Decimal("100")
            total_earning_amount += calculated_earning

            assigned_course_list.append({
                "contract_id": contract.id,
                "course_id": contract.course.id if contract.course else None,
                "course_title": contract.course.title if contract.course else None,
                "organization_id": contract.organization.id if contract.organization else None,
                "organization_name": contract.organization.name if contract.organization else None,
                "discount_price": discount_price,
                "assigned_percentage": assigned_percentage,
                "calculated_earning": calculated_earning,
                "expiry_date": contract.expiry_date,
                "status": contract.status,
            })

        total_assigned_courses = contracts.values("course_id").distinct().count()

        serializer = EarningsChartSerializer({
            "total_assigned_courses": total_assigned_courses,
            "total_earning_amount": total_earning_amount,
            "assigned_course_list": assigned_course_list,
        })

        return APIResponse.success(
            message="Instructor earnings chart retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
        
        


# View for sending message       
class ContractUserMessageSendAPIView(APIView):
    paginator_class = CustomPagination

    def post(self, request):
        serializer = ContractUsUserMessageSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            contract_message = serializer.save()
            response_serializer = ContractUsUserMessageSerializer(contract_message)

            return APIResponse.success(
                message="Message sent successfully.",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        return APIResponse.error(
            message="Failed to send message.",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
    def get(self, request):

        messages = ContractUserMessage.objects.all().order_by("-created_at")
        paginator=self.paginator_class()
        paginated_messages=paginator.paginate_queryset(messages,request,view=self)
        serializer = ContractUsUserMessageSerializer(
            paginated_messages,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(
            data=serializer.data,
            message="Messages retrieved successfully."
        )
    
        
        
class ContractUsMessageDetailsAPIView(APIView):

    def get(self, request, message_id):
        try:
            message = ContractUserMessage.objects.get(id=message_id)
        except ContractUserMessage.DoesNotExist:
            return APIResponse.error(
                message="Message not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ContractUsUserMessageSerializer(message, context={"request": request})

        return APIResponse.success(
            message="Message details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
  
        
