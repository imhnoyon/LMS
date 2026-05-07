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
    path("instructors/live-classes/",InstructorOrganizationLiveClassStatsView.as_view(),name="organization-instructor-list"),
    path("live-classes/<int:course_id>/",LiveClassOrganizationInstructorManageView.as_view(),name="organization-course-dashboard"),
    path("courses/<int:course_id>/live-session/upload/", OrganizationLiveSessionUploadView.as_view(), name="live-session-upload"),
    
    # My courses 
    path("my-courses/", CourseListByOrganizationView.as_view(), name="my-courses"),
    
    # Organization Earnings Dashboard
    path("organization-deshboard/", OrganizationDashboardView.as_view(), name="organization-earnings"),
    path("organization-earnings/dashboard/",OrganizationEarningsDashboardView.as_view(),name="organization-earnings-dashboard"),
    
    
     path("admin/organizations/", OrganizationAdminListAPIView.as_view(),name="admin-organization-list"),
     path("admin/organizations/<int:pk>/", OrganizationAdminDetailAPIView.as_view(),name="admin-organization-detail"),
]
