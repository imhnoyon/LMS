from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from apps.courses.models import Course, LiveClass
from apps.courses.serializers import LiveClassSerializer
from apps.payments.models import Commission, Payment
from utils.permissions import IsInstructor, IsOrganization
from .models import Organization, Membership, Invitation
from .serializers import LiveSessionUploaderSerializer, OrganizationMembershipSerializer, UnverifiedOrganizationListSerializer, InvitationSerializer
from utils.paginations import CustomPagination
from utils.api_response import APIResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum
from apps.users.models import User
from utils.emails import send_invitation_email
from decimal import Decimal

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
        membership = Membership.objects.filter(
            user=request.user, 
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).first()

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
                
                # ✅ Update Instructor model flag
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

        total_courses = organization.total_courses

        return APIResponse.success(
            message="Organization instructor dashboard fetched successfully.",
            data={
                "stats": {
                    "total_instructors": total_instructors,
                    "active_instructors": active_instructors,
                    "pending_invitations": pending_invitations,
                    "total_courses": total_courses,
                },
                "memberships list": serializer.data,
            },
            status_code=200
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