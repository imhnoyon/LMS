from django.urls import path
from .views import *
    

urlpatterns = [
    
    # For Admin to view unverified organizations
    path("unverified-organizations/", UnverifiedOrganizationListView.as_view(), name="unverified-organizations"),
    path("approve-organization/<int:pk>/", ApproveOrganizationView.as_view(), name="approve-organization"),
    path("reject-organization/<int:pk>/", RejectOrganizationView.as_view(), name="reject-organization"),

    # Organization Invitation
    path("invite/", InviteInstructorView.as_view(), name="organization-invite"),
    path("invitation/<uuid:token>/", InvitationDetailView.as_view(), name="invitation-detail"),
    path("invitation/respond/<uuid:token>/", RespondInvitationView.as_view(), name="invitation-respond"),
    
    path("organization/instructors/dashboard/",OrganizationInstructorDashboardView.as_view(),name="organization-instructor-dashboard"),
]
