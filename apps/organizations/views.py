from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from utils.permissions import IsOrganization
from .models import Organization, Membership, Invitation
from .serializers import OrganizationMembershipSerializer, UnverifiedOrganizationListSerializer, InvitationSerializer
from utils.paginations import CustomPagination
from utils.api_response import APIResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
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

            # Ensure user has correct platform role
            if invitation.role == Membership.Role.INSTRUCTOR and request.user.role != 'instructor':
                request.user.role = 'instructor'
                request.user.save(update_fields=['role'])

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