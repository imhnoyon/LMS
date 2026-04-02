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
from apps.payments.models import Invoice
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
    
    
    
# Withdrawn api
class CreateConnectAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.is_instructor:
            return APIResponse.error(
                message="Only intructors can create a connect account.",
                status_code=403
            )

        try:
            if not user.stripe_account_id:
                account = stripe.Account.create(
                    type="express",
                    country="US",  # need to set supported country for your business/user
                    email=user.email,
                    capabilities={
                        "transfers": {"requested": True},
                    },
                )
                user.stripe_account_id = account.id
                user.save(update_fields=["stripe_account_id"])
            else:
                account = stripe.Account.retrieve(user.stripe_account_id)

            refresh_url = request.build_absolute_uri(reverse('stripe-reauth'))
            return_url = request.build_absolute_uri(reverse('stripe-return'))

            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type="account_onboarding",
            )

            return APIResponse.success(
                message="Stripe onboarding link generated successfully",
                data={
                    "stripe_account_id": account.id,
                    "onboarding_url": account_link.url,
                    "charges_enabled": account.get("charges_enabled", False),
                    "payouts_enabled": account.get("payouts_enabled", False),
                    "details_submitted": account.get("details_submitted", False),
                }
            )
        except stripe.error.StripeError as e:
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=400
            )
            
            
#Instructor login own deshboard
class StripeDashboardLoginLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.stripe_account_id:
            return APIResponse.error(
                message="Stripe account not connected.",
                status_code=400
            )

        try:
            login_link = stripe.Account.create_login_link(user.stripe_account_id)
            return APIResponse.success(
                message="Login link created successfully",
                data={"url": login_link.url}
            )
        except stripe.error.StripeError as e:
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=400
            )
            
            
# Withdraw Request views
class CreatorWithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user

        if not user.creator:
            return APIResponse.error(
                message="Only creators can withdraw.",
                status_code=403
            )

        amount = request.data.get("amount")
        if not amount:
            return APIResponse.error(
                message="Amount is required.",
                status_code=400
            )

        try:
            amount = Decimal(str(amount))
        except Exception:
            return APIResponse.error(
                message="Invalid amount format.",
                status_code=400
            )

        if amount <= 0:
            return APIResponse.error(
                message="Amount must be greater than 0.",
                status_code=400
            )

        available_balance = get_creator_available_balance(user)

        if amount > available_balance:
            return APIResponse.error(
                message=f"Insufficient balance. Available balance is {available_balance}.",
                status_code=400
            )

        stripe_status = refresh_stripe_account_status(user)
        if not stripe_status:
            return APIResponse.error(
                message="No connected Stripe account found. Please connect Stripe first.",
                status_code=400
            )

        if not stripe_status["details_submitted"]:
            return APIResponse.error(
                message="Stripe onboarding is not completed.",
                status_code=400
            )

        if not stripe_status["payouts_enabled"]:
            return APIResponse.error(
                message="Stripe payouts are not enabled for this account.",
                status_code=400
            )

        withdrawal = Withdrawal.objects.create(
            creator=user,
            amount=amount,
            previous_balance=available_balance,
            current_balance=available_balance - amount,
            status="pending",
        )

        return APIResponse.success(
            message="Withdrawal request submitted successfully",
            data={
                "withdraw_id": withdrawal.withdraw_id,
                "amount": str(withdrawal.amount),
                "previous_balance": str(withdrawal.previous_balance),
                "current_balance": str(withdrawal.current_balance),
                "status": withdrawal.status,
            }
        )