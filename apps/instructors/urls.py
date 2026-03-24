from django.urls import path
from apps.instructors.views import *

urlpatterns = [
    path("pending-instructors/", PendingInstructorListView.as_view(), name="pending-instructors"),
    path("approve-instructor/<str:pk>/", ApproveInstructorView.as_view(), name="approve-instructor"),
    path("feature-instructor/<str:pk>/", FeatureApprovedInstructorView.as_view(), name="feature-instructor"),
    path("delete-instructor/<str:pk>/", DeleteInstructorView.as_view(), name="delete-instructor"),
]