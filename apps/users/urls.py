from django.urls import path
from apps.users.views import *


# Users app URLs
urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="user-register"),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', SignInView.as_view(), name='login'),
    path('resend-verification/', ResendVerificationCodeView.as_view(), name='resend-verification'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-reset-code/', VerifyResetCodeView.as_view(), name='verify-reset-code'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='refresh-token'),
    
    
    # All User list shown in admin panel with course count
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
    path("send-email/", SendEmailView.as_view(), name="send-email"),
    path("block/<uuid:pk>/", BlockUserView.as_view(), name="block-unblock-user"),
    path("unblock/<uuid:pk>/", UnblockUserView.as_view(), name="unblock-user"),
    
    path("admin/dashboard-data/", AdminDashboardStatsView.as_view(), name="admin-dashboard-data"),
    path("admin/payments/", AdminPaymentsDeshboardView.as_view(), name="admin-payments"),
    path("admin/analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    
    
]
