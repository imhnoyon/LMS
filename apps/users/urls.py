from django.urls import path
from apps.users.views import (
    RegisterAPIView,
    VerifyEmailView,
    SignInView,
    ResendVerificationCodeView,
    ForgotPasswordView,
    VerifyResetCodeView,
    ResetPasswordView,
    CustomTokenRefreshView
)


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
]