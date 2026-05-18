from django.urls import path
from .views import *
from .analytics_views import *
    

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
    path("organization-instructors-contracts/",OrInstructorListAPIView.as_view(),name="organization-instructors"),
    path("my-organization-courses/",MyOrganizationCourseListAPIView.as_view(),name="my-organization-courses"),
    path("contracts-instructors/",ContractListCreateAPIView.as_view(),name="contracts"),
    path("contracts-instructors/<int:contract_id>/",ContractListCreateAPIView.as_view(),name="contract-update"),
    path("organization-contracts-details/<int:contract_id>/", ContractDetailAPIView.as_view(), name="organization-contracts-detail"),
    path("members-analytics/",OrganizationMemberAnalyticsView.as_view(),name="members-analytics"),
    
    path("organization-profile/",OrganizationProfileView.as_view(),name="organization-profile-update"),
    
    # Organization Analytics & Reporting APIs
    path("dashboard-statistics/", DashboardStatisticsView.as_view(), name="dashboard-statistics"),
    path("revenue-trends/", RevenueTrendsView.as_view(), name="revenue-trends"),
    path("daily-revenue/", DailyRevenueChartView.as_view(), name="daily-revenue"),
    path("course-analytics/", CourseAnalyticsView.as_view(), name="course-analytics"),
    path("top-courses/", TopCoursesView.as_view(), name="top-courses"),
    path("recent-activity/", RecentActivityView.as_view(), name="recent-activity"),
    path("ratings-breakdown/", RatingsBreakdownView.as_view(), name="ratings-breakdown"),
    path("comprehensive-report/", ComprehensiveReportView.as_view(), name="comprehensive-report"),
    
    
    
    path("admin/organizations/", OrganizationAdminListAPIView.as_view(),name="admin-organization-list"),
    path("admin/organizations/<int:pk>/", OrganizationAdminDetailAPIView.as_view(),name="admin-organization-detail"),
    path("organization/earnings/", OrganizationEarningsView.as_view(), name="organization-earnings"),
    path("membership/toggle/<int:pk>/", ToggleMembershipStatusAPIView.as_view(), name="toggle-membership-status"),
    path("organization/profile/",OrganizationProfileAPIView.as_view(),name="organization-profile"),
    
    
    
    # organization members instructor 
    path("instructor/organizations/", InstructorOrganizationListAPIView.as_view(), name="instructor-organizations"),
    
    path("instructor/contracts/courses/",InstructorContractCourseListView.as_view(),name="instructor-contract-course-list",),
    path("instructor/contracts/categories/",InstructorContractCategoryListView.as_view(),name="instructor-contract-category-list",),
    path("instructor/earnings/chart/",InstructorEarningsChartAPIView.as_view(),name="instructor-earnings-chart",),
    
    
    # path("earnings/summary/", EarningsChartSerializer.as_view(), name="earnings-summary"),
    

]
