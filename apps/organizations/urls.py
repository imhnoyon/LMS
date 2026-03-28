from django.urls import path
from .views import *
    

urlpatterns = [
    
    # For Admin to view unverified organizations
    path("unverified-organizations/", UnverifiedOrganizationListView.as_view(), name="unverified-organizations"),
    path("approve-organization/<int:pk>/", ApproveOrganizationView.as_view(), name="approve-organization"),
    path("reject-organization/<int:pk>/", RejectOrganizationView.as_view(), name="reject-organization"),
]
