from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from utils.api_response import APIResponse
from apps.orders.models import Order
from .models import Payment
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import stripe
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.enrollments.models import Enrollment
from apps.payments.models import Invoice, Withdrawal
from django.shortcuts import render
from django.views import View
from datetime import date
from django.urls import reverse


# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateStripeCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        user = request.user

        try:
            order = Order.objects.get(id=order_id, user=user)
        except Order.DoesNotExist:
            return APIResponse.error(
                message="Order not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if order.status != "pending":
            return APIResponse.error(
                message="Only pending orders can be paid.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if order.total_amount <= Decimal("0.00"):
            return APIResponse.error(
                message="Invalid order amount.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        payment = Payment.objects.create(
            user=user,
            order=order,
            amount=order.total_amount,
            payment_method="stripe",
            status="pending",
            currency="USD",
        )

        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                customer_email=user.email,
                line_items=[
                    {
                        "price_data": {
                            "currency": payment.currency.lower(),
                            "product_data": {
                                "name": f"Order {order.order_id}",
                            },
                            "unit_amount": int(order.total_amount * 100),
                        },
                        "quantity": 1,
                        
                    }
                ],
                success_url=f"{request.build_absolute_uri('/api/v1/payments/stripe/success/')}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{request.build_absolute_uri('/api/v1/payments/stripe/cancel/')}",
                metadata={
                    "payment_id": str(payment.id),
                    "order_id": str(order.id),
                    "user_id": str(user.id),
                },
                payment_intent_data={
                    "metadata": {
                        "payment_id": str(payment.id),
                        "order_id": str(order.id),
                        "user_id": str(user.id),
                    }
                },
            )

            payment.transaction_id = session.id
            payment.save(update_fields=["transaction_id"])

            return APIResponse.success(
                message="Stripe checkout session created successfully.",
                data={
                    "checkout_url": session.url,
                    "session_id": session.id,
                    "payment_id": payment.id,
                },
                status_code=status.HTTP_200_OK
            )

        except stripe.error.StripeError as e:
            payment.status = "failed"
            payment.save(update_fields=["status"])
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            


from datetime import date
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        event = self._construct_event(request)
        if isinstance(event, dict) and event.get("error_response"):
            return event["error_response"]

        event_type = event["type"]
        stripe_object = event["data"]["object"]

        event_handlers = {
            "checkout.session.completed": self.handle_checkout_completed,
            "checkout.session.expired": self.handle_checkout_expired,
            "payment_intent.succeeded": self.handle_payment_intent_succeeded,
            "payment_intent.created": self.handle_payment_intent_created,
            "charge.succeeded": self.handle_charge_succeeded,
            "charge.updated": self.handle_charge_updated,
        }

        handler = event_handlers.get(event_type)
        if handler:
            handler(stripe_object)

        return APIResponse.success(
            message="Webhook processed successfully.",
            status_code=200
        )

    def _construct_event(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            return stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return {
                "error_response": APIResponse.error(
                    message="Invalid webhook payload.",
                    status_code=400
                )
            }
        except stripe.error.SignatureVerificationError:
            return {
                "error_response": APIResponse.error(
                    message="Invalid webhook signature.",
                    status_code=400
                )
            }

    @transaction.atomic
    def handle_checkout_completed(self, session):
        payment = self._get_payment_from_session(session)
        if not payment:
            return

        if payment.status == "success":
            return

        payment_method = self._get_payment_method(session)

        self._mark_payment_success(payment, session, payment_method)
        self._mark_order_paid(payment.order)
        self._create_enrollments(payment)
        self._create_invoice(payment)

    @transaction.atomic
    def handle_checkout_expired(self, session):
        payment = self._get_payment_from_session(session)
        if not payment:
            return

        if payment.status == "pending":
            payment.status = "cancelled"
            payment.save(update_fields=["status", "updated_at"])

    def _get_payment_from_session(self, session):
        metadata = session.metadata.to_dict() if session.metadata else {}
        payment_id = metadata.get("payment_id")

        if not payment_id:
            return None

        try:
            return Payment.objects.select_related("order", "user").get(id=payment_id)
        except Payment.DoesNotExist:
            return None

    def _get_payment_method(self, session):
        payment_intent_id = getattr(session, "payment_intent", None)
        if not payment_intent_id:
            return "stripe"

        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            payment_method_id = payment_intent.get("payment_method")

            if not payment_method_id:
                return "stripe"

            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            method_type = payment_method.type

            if method_type == "card":
                card_data = getattr(payment_method, "card", None)
                wallet = getattr(card_data, "wallet", None) if card_data else None
                if wallet and getattr(wallet, "type", None):
                    return wallet.type

            return method_type
        except Exception:
            return "stripe"

    def _mark_payment_success(self, payment, session, payment_method):
        payment.status = "success"
        payment.transaction_id = session.id
        payment.gateway_payment_id = session.payment_intent
        payment.payment_method = payment_method
        payment.paid_at = timezone.now()
        payment.save(update_fields=[
            "status",
            "transaction_id",
            "gateway_payment_id",
            "payment_method",
            "paid_at",
            "updated_at",
        ])

    def _mark_order_paid(self, order):
        order.status = "paid"
        order.save(update_fields=["status"])

    def _create_enrollments(self, payment):
        order_items = payment.order.items.select_related("course").all()

        for item in order_items:
            Enrollment.objects.get_or_create(
                user=payment.user,
                course=item.course,
                defaults={
                    "order": payment.order,
                    "is_active": True,
                    "enrolled_at": timezone.now(),
                }
            )

    def _create_invoice(self, payment):
        invoice_exists = Invoice.objects.filter(
            user=payment.user,
            amount=payment.amount,
            invoice_date=date.today(),
            status="paid"
        ).exists()

        if invoice_exists:
            return

        Invoice.objects.create(
            user=payment.user,
            payment_method=payment.payment_method or "stripe",
            amount=payment.amount,
            currency=payment.currency or "USD",
            status="paid",
            invoice_date=date.today(),
        )

    def handle_payment_intent_succeeded(self, payment_intent):
        pass

    def handle_payment_intent_created(self, payment_intent):
        pass

    def handle_charge_succeeded(self, charge):
        pass

    def handle_charge_updated(self, charge):
        pass

class PaymentSuccessView(View):
    """Render payment success page"""
    def get(self, request):
        session_id = request.GET.get('session_id', '')
        context = {
            'session_id': session_id,
            'current_time': timezone.now()
        }
        return render(request, 'payment_success.html', context)


class PaymentCancelView(View):
    """Render payment cancellation page"""
    def get(self, request):
        context = {
            'current_time': timezone.now()
        }
        return render(request, 'payment_cancel.html', context)
    
    
 