from django.urls import path
from apps.instructors.views import *

urlpatterns = [
    path("pending-instructors/", PendingInstructorListView.as_view(), name="pending-instructors"),
    path("approve-instructor/<str:pk>/", ApproveInstructorView.as_view(), name="approve-instructor"),
    path("feature-instructor/<str:pk>/", FeatureApprovedInstructorView.as_view(), name="feature-instructor"),
    path("delete-instructor/<str:pk>/", DeleteInstructorView.as_view(), name="delete-instructor"),
    path("withdrawals/", WithdrawalRequestListView.as_view(),name="withdrawal-list"),
    
    
    # course list seen by instructor approve or not
    path("courses/", CourseListView.as_view(), name="course-list"),
    
    # instructor profile
    path("profile/", InstructorProfileUpdateView.as_view(), name="instructor-profile"),
    path("dashboard/", InstructorDashboardView.as_view(), name="instructor-dashboard"),
    path("earnings/", InstructorEarningsView.as_view(), name="instructor-earnings"),
]