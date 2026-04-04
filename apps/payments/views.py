from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from utils.api_response import APIResponse
from apps.orders.models import Order
from utils.permissions import IsInstructor
from .models import Payment
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework import status
import stripe
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.enrollments.models import Enrollment
from apps.payments.models import Invoice, Withdrawal, Commission
from django.shortcuts import get_object_or_404, render
from django.views import View
from datetime import date
from django.urls import reverse
from django.db.models import Sum


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
        self._create_course_commissions(payment)

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
    
   

    def _create_course_commissions(self, payment):
        instructor_rate = Decimal(str(settings.INSTRUCTOR_RATE))
        platform_rate = Decimal(str(settings.PLATFORM_RATE))

        order_items = payment.order.items.select_related(
            "course", "course__instructor"
        ).all()

        for item in order_items:
            course = item.course
            instructor = getattr(course, "instructor", None)

            if not course or not instructor:
                continue

            item_total = Decimal(str(getattr(item, "paid_price", None) or item.price))

            instructor_amount = (item_total * instructor_rate).quantize(Decimal("0.01"))
            platform_amount = (item_total * platform_rate).quantize(Decimal("0.01"))

            Commission.objects.get_or_create(
                user=instructor,
                course=course,
                defaults={
                    "payment_method": payment.payment_method or "Stripe",
                    "order_amount": item_total,
                    "commission_amount": instructor_amount,
                }
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
    
class StripeReturnPageView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return render(request, "account_connected_success.html")


class PaymentCancelView(View):
    """Render payment cancellation page"""
    def get(self, request):
        context = {
            'current_time': timezone.now()
        }
        return render(request, 'payment_cancel.html', context)
    
    
class StripeCancelPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return render(request, "account_connected_cancel.html")
 
 
# Withdrawa views and other payment-related views would go here, but are not included in this snippet.

class CreateStripeConnectAccountView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    def post(self, request):
        user = request.user
        instructor = user.instructor   

        try:
           
            if not instructor.stripe_account_id:
                account = stripe.Account.create(
                    type="express",
                    country="US",  # 👉 change dynamically later
                    email=user.email,
                    capabilities={
                        "transfers": {"requested": True},
                        "card_payments": {"requested": True},
                    },
                )

                instructor.stripe_account_id = account.id
                instructor.save(update_fields=["stripe_account_id"])

            else:
                account = stripe.Account.retrieve(instructor.stripe_account_id)

            refresh_url = request.build_absolute_uri(reverse("stripe-return-page"))
            return_url = request.build_absolute_uri(reverse("stripe-cancel"))

            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type="account_onboarding",
            )

            details_submitted = getattr(account, "details_submitted", False)
            if details_submitted and not instructor.stripe_onboarding_completed:
                instructor.stripe_onboarding_completed = True
                instructor.save(update_fields=["stripe_onboarding_completed"])

            #  4. Response
            return APIResponse.success(
                message="Stripe onboarding link generated successfully",
                data={
                    "stripe_account_id": account.id,
                    "onboarding_url": account_link.url,
                    "charges_enabled": getattr(account, "charges_enabled", False),
                    "payouts_enabled": getattr(account, "payouts_enabled", False),
                    "details_submitted": details_submitted,
                },
                status_code=status.HTTP_200_OK
            )

        except stripe.error.StripeError as e:
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=400
            )
            
            
            
class StripeDashboardLoginLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        instructor = user.instructor

        if not instructor.stripe_account_id:
            return APIResponse.error(
                message="Stripe account not connected.",
                status_code=400
            )

        try:
            login_link = stripe.Account.create_login_link(instructor.stripe_account_id)
            return APIResponse.success(
                message="Login link created successfully",
                data={"url": login_link.url}
            )
        except stripe.error.StripeError as e:
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=400
            )
            
            
            
            
class WithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    @transaction.atomic
    def post(self, request):
        user = request.user

        amount = request.data.get("amount")
        withdraw_method = request.data.get("withdraw_method", "unknown")

        if not amount:
            return APIResponse.error("Amount is required", 400)

        try:
            amount = Decimal(str(amount))
        except:
            return APIResponse.error("Invalid amount", 400)

        if amount <= 0:
            return APIResponse.error("Amount must be greater than 0", 400)

        #  Total earnings (from commission)
        total_earnings = Commission.objects.filter(
            user=user
        ).aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")

        #  Already withdrawn
        withdrawn_amount = Withdrawal.objects.filter(
            user=user,
            status__in=["pending", "completed"]
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        available_balance = total_earnings - withdrawn_amount

        if amount > available_balance:
            return APIResponse.error(
                f"Insufficient balance. Available: {available_balance}", 400
            )

        #  Stripe account check
        instructor = user.instructor
        if not instructor.stripe_account_id:
            return APIResponse.error("Stripe account not connected", 400)

        try:
            account = stripe.Account.retrieve(instructor.stripe_account_id)
        except Exception:
            return APIResponse.error("Stripe account error", 400)

        if not account.payouts_enabled:
            return APIResponse.error("Stripe payouts not enabled", 400)

        #  Retrieve Bank / Card details automatically from Stripe
        bank_name = request.data.get("bank_name", "")
        bank_last4 = ""

        external_accounts = getattr(account, "external_accounts", None)
        if external_accounts and getattr(external_accounts, "data", []):
            default_acc = external_accounts.data[0]
            acc_object = getattr(default_acc, "object", "")
            
            if acc_object == "bank_account":
                bank_name = getattr(default_acc, "bank_name", bank_name)
                bank_last4 = getattr(default_acc, "last4", "")
            elif acc_object == "card":
                brand = getattr(default_acc, "brand", "Card")
                bank_name = f"{brand} Card"
                bank_last4 = getattr(default_acc, "last4", "")

        #  Create withdrawal
        withdrawal = Withdrawal.objects.create(
            user=user,
            amount=amount,
            bank_name=bank_name,
            bank_last4=bank_last4,
            previous_balance=available_balance,
            current_balance=available_balance - amount,
            withdraw_method=withdraw_method,
            status="pending",
        )

        return APIResponse.success(
            message="Withdraw request submitted",
            data={
                "withdraw_id": withdrawal.withdraw_id,
                "amount": str(withdrawal.amount),
                "status": withdrawal.status,
            }
        )




# Admin view to approve or reject withdrawal requests
class ApproveWithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @transaction.atomic
    def post(self, request, withdraw_id):
        status_value = request.data.get("status")

        if not withdraw_id:
            return APIResponse.error(
                message="withdraw_id is required.",
                status_code=400
            )

        if not status_value:
            return APIResponse.error(
                message="status is required.",
                status_code=400
            )

        status_value = status_value.lower()

        if status_value not in ["completed", "rejected"]:
            return APIResponse.error(
                message="Invalid status. Use 'completed' or 'rejected'.",
                status_code=400
            )

        withdrawal = get_object_or_404(Withdrawal, withdraw_id=withdraw_id)

        if withdrawal.status != "pending":
            return APIResponse.error(
                message="This withdrawal has already been processed.",
                status_code=400
            )

        instructor = withdrawal.user.instructor

        # cancel flow
        if status_value == "rejected":
            withdrawal.status = "rejected"
            withdrawal.failure_reason = request.data.get("failure_reason", "Rejected by admin.")
            withdrawal.save(update_fields=["status", "failure_reason", "updated_at"])

            return APIResponse.success(
                message="Withdrawal rejected successfully.",
                data={
                    "withdraw_id": withdrawal.withdraw_id,
                    "status": withdrawal.status,
                    "failure_reason": withdrawal.failure_reason,
                },
                status_code=200
            )

        # completed flow
        try:
            transfer = stripe.Transfer.create(
                amount=int(withdrawal.amount * 100),
                currency="usd",
                destination=instructor.stripe_account_id
            )

            withdrawal.status = "completed"
            withdrawal.stripe_transfer_id = transfer.id
            withdrawal.failure_reason = None
            withdrawal.save(update_fields=[
                "status",
                "stripe_transfer_id",
                "failure_reason",
                "updated_at"
            ])

            return APIResponse.success(
                message="Withdrawal approved and paid successfully.",
                data={
                    "withdraw_id": withdrawal.withdraw_id,
                    "status": withdrawal.status,
                    "transfer_id": transfer.id
                },
                status_code=200
            )

        except Exception as e:
            withdrawal.status = "cancelled"
            withdrawal.failure_reason = str(e)
            withdrawal.save(update_fields=["status", "failure_reason", "updated_at"])

            return APIResponse.error(
                message="Transfer failed.",
                errors={"stripe_error": str(e)},
                status_code=400
            )
            
# Instructor view to cancel their pending withdrawal request           
class InstructorCancelWithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsInstructor]

    @transaction.atomic
    def post(self, request, withdraw_id):
        withdrawal = get_object_or_404(
            Withdrawal,
            withdraw_id=withdraw_id,
            user=request.user
        )

        if withdrawal.status != "pending":
            return APIResponse.error(
                message="Only pending withdrawal requests can be cancelled.",
                status_code=400
            )

        withdrawal.status = "cancelled"
        withdrawal.failure_reason = request.data.get(
            "failure_reason",
            "Cancelled by instructor."
        )
        withdrawal.save(update_fields=["status", "failure_reason", "updated_at"])

        return APIResponse.success(
            message="Withdrawal request cancelled successfully.",
            data={
                "withdraw_id": withdrawal.withdraw_id,
                "status": withdrawal.status,
                "failure_reason": withdrawal.failure_reason,
            },
            status_code=200
        )