from django.urls import path
from .views import *

urlpatterns = [
    path("affiliates/", AffiliateListView.as_view(), name="affiliate-list"),
    path("affiliates/status/<str:pk>/", UpdateAffiliateStatusView.as_view(), name="affiliate-status-update"),
    path("delete-affiliate/<str:pk>/", DeleteAffiliateView.as_view(), name="delete-affiliate"),
    
    # Affliate Deshboard
    path("affiliate/courses/", AffiliateCourseListView.as_view(), name="affiliate-course-list"),
    path("generate-course-referral-link/<int:course_id>/", GenerateAffiliateCourseLinkView.as_view(), name="generate-affiliate-course-link"),
    path("track-referral-click/", TrackReferralClickView.as_view(), name="track-referral-click"),
    path("affiliate/dashboard/", AffiliateDashboardView.as_view(), name="affiliate-dashboard"),
    path("affiliate/wallet/", AffiliateWalletView.as_view(), name="affiliate-wallet"),
    
    # Affiliate Profile
    path("affiliate/profile/", AffiliateProfileView.as_view(), name="affiliate-profile"),
]