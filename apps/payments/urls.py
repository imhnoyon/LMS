from django.urls import path
from .views import *

urlpatterns = [
    path("stripe/checkout/<int:order_id>/", CreateStripeCheckoutSessionView.as_view(), name="stripe-checkout"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("stripe/success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("stripe/cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
    
    
    
]