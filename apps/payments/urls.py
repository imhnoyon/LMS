from django.urls import path
from .views import *

urlpatterns = [
    path("stripe/checkout/<int:order_id>/", CreateStripeCheckoutSessionView.as_view(), name="stripe-checkout"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    # Success and Cancel pages
    path("stripe/success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("stripe/cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
    
    
    
    # Instructor Withdrawals
    path("stripe/connect/", CreateStripeConnectAccountView.as_view()),
    path("stripe/dashboard-link/", StripeDashboardLoginLinkView.as_view()),
    path("withdraw/request/", WithdrawRequestView.as_view()),
    path("withdraw/approve/<str:withdraw_id>/", ApproveWithdrawView.as_view()),
    path("instructor/withdraw/cancel/<str:withdraw_id>/",InstructorCancelWithdrawView.as_view(),name="instructor-withdraw-cancel",),
    
    # Affiliate withdrawals
    path("affiliate/stripe/connect/", AffiliateCreateStripeConnectAccountView.as_view()),
    path("affiliate/stripe/dashboard-link/", AffiliateStripeDashboardLoginLinkView.as_view()),
    path("affiliate/withdraw/request/", AffiliateWithdrawRequestView.as_view()),
    
    # Organization Withdrawals
    path("organization/stripe/connect/", OrganizationCreateStripeConnectAccountView.as_view()),
    path("organization/stripe/dashboard-link/", OrganizationStripeDashboardLoginLinkView.as_view()),
    path("organization/withdraw/request/", OrganizationWithdrawRequestView.as_view()),
    
    path("stripe/return-page/", StripeReturnPageView.as_view(), name="stripe-return-page"),
    path("stripe/cancel/", StripeCancelPageView.as_view(), name="stripe-cancel"),
]