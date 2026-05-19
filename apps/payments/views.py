from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from apps.affiliates.models import Affiliate, AffiliateCommission
from apps.notifications.models import Notification
from apps.organizations.models import Membership, Organization
from apps.users.models import User
from utils.api_response import APIResponse
from apps.orders.models import Order
from utils.permissions import IsAffiliate, IsInstructor, IsOrganization
from .models import Payment
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework import status
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
from apps.organizations.models import Membership
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
from apps.messaging.models import Conversation


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
            currency="EUR",
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
                success_url=f"{settings.FONTEND_SUCCESSFUL_URL}/en/dashboard",
                cancel_url=f"{settings.FONTEND_SUCCESSFUL_URL}/en/dashboard",
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
        # Create conversations between student and instructors of purchased courses
        self._create_conversations(payment)
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
            return Payment.objects.select_for_update().select_related("order", "user").get(id=payment_id)
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
        payment_intent_id = getattr(session, "payment_intent", None)
        if not payment_intent_id and isinstance(session, dict):
            payment_intent_id = session.get("payment_intent")

        payment.status = "success"
        payment.transaction_id = session.id
        payment.gateway_payment_id = payment_intent_id
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
            currency=payment.currency or "EUR",
            status="paid",
            invoice_date=date.today(),
        )
    
   

    def _create_course_commissions(self, payment):
        from django.db.models import F
        platform_fee_rate = settings.PLATFORM_FEE_RATE
        total_platform_revenue = Decimal("0.00")
        
        order_items = payment.order.items.select_related(
            "course", "course__instructor", "course__organization"
        ).all()

        for item in order_items:
            course = item.course
            if not course:
                continue
            
            item_total = Decimal(str(getattr(item, "paid_price", Decimal("0.00"))))
            
            # Phase 1: Platform Fee (Always collect this for every item)
            platform_amount = (item_total * platform_fee_rate).quantize(Decimal("0.01"))
            total_platform_revenue += platform_amount
            remaining_for_payouts = item_total - platform_amount

            payout_user = None
            
            # 🏢 Organization logic: If the course belongs to an organization, find the admin
            if course.organization:
                admin_membership = Membership.objects.filter(
                    organization=course.organization,
                    role=Membership.Role.ADMIN
                ).select_related("user").first()
                if admin_membership:
                    payout_user = admin_membership.user
            
            # 👨‍🏫 Fallback: If no organization or admin found, use the direct instructor
            if not payout_user:
                payout_user = course.instructor

            if not payout_user:
                # If there's no one to pay the remainder to, we still collected the platform fee
                continue

            # Phase 2: Affiliate Commission
            affiliate_amount = Decimal("0.00")
            referral_code = getattr(item, "referral_code", None)
            from apps.affiliates.models import AffiliateCourseLink, AffiliateCommission, AffiliateReferralClick
            
            active_click = None
            if not referral_code:
                active_click = AffiliateReferralClick.objects.filter(
                    clicked_by=payment.user,
                    course=course,
                    is_converted=False
                ).order_by("-clicked_at").first()
                
                if active_click:
                    referral_code = active_click.code

            if referral_code:
                link = AffiliateCourseLink.objects.filter(code=referral_code, course=course).first()
                if link:
                    affiliate = link.affiliate
                    aff_comm_config = AffiliateCommission.objects.filter(affiliate=affiliate, product=course).first()
                    aff_rate_raw = getattr(aff_comm_config, "commission_rate", affiliate.commission_rate)

                    aff_multiplier = aff_rate_raw if aff_rate_raw < 1 else (aff_rate_raw / Decimal("100"))
                    affiliate_amount = (item_total * aff_multiplier).quantize(Decimal("0.01"))

            final_instructor_amount = remaining_for_payouts - affiliate_amount
            if final_instructor_amount < 0: final_instructor_amount = 0

            # 💰 Record Instructor Commission
            Commission.objects.create(
                user=payout_user,
                course=course,
                payment_method=payment.payment_method or "Stripe",
                order_amount=item_total,
                commission_amount=final_instructor_amount,
            )

            # 💸 Record Affiliate payout
            if affiliate_amount > 0:
                affiliate.total_earned = F("total_earned") + affiliate_amount
                affiliate.save(update_fields=["total_earned"])
                if active_click:
                    active_click.is_converted = True
                    active_click.save(update_fields=["is_converted"])
                    
                AffiliateCommission.objects.create(
                    affiliate=affiliate,
                    product=course,  
                    order=payment.order,
                    commission_rate=affiliate_amount, 
                )

        # 🏢 Update Platform Admin Revenue ONCE for the entire order
        if total_platform_revenue > 0:
            User.objects.filter(role="owner").update(
                platform_revenue=F("platform_revenue") + total_platform_revenue
            )

    def _create_conversations(self, payment):
        """Ensure a Conversation exists between the purchasing user and each course instructor."""
        try:
            order_items = payment.order.items.select_related("course", "course__instructor").all()
        except Exception:
            return

        student = payment.user

        for item in order_items:
            course = getattr(item, "course", None)
            if not course:
                continue

            instructor = getattr(course, "instructor", None)
            if not instructor:
                continue

            # don't create conversation with self
            if instructor.id == student.id:
                continue

            # Only create conversation if an enrollment exists (safety check)
            enrolled = Enrollment.objects.filter(user=student, course=course).exists()
            if not enrolled:
                continue

            # Check for existing two-person conversation
            conv = Conversation.objects.filter(participants=student).filter(participants=instructor).distinct().first()
            if not conv:
                conv = Conversation.objects.create()
                conv.participants.add(student, instructor)
        

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
                    country="IE",  # Ireland for Euro based accounts
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

            # SUCCESS return (on completion)
            return_url = request.build_absolute_uri(reverse("stripe-return-page"))
            # REFRESH / ERROR return (if session expired or premature exit)
            refresh_url = request.build_absolute_uri(reverse("stripe-cancel"))

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

        if status_value not in ["approved", "rejected"]:
            return APIResponse.error(
                message="Invalid status. Use 'approved' or 'rejected'.",
                status_code=400
            )

        withdrawal = get_object_or_404(Withdrawal, withdraw_id=withdraw_id)

        if withdrawal.status != "pending":
            return APIResponse.error(
                message="This withdrawal has already been processed.",
                status_code=400
            )

        user = withdrawal.user
        payout_profile = None
        stripe_account_id = None
        account_type = None

        # Organization admin check
        if hasattr(user, "organization_memberships") and user.organization_memberships.filter(role=Membership.Role.ADMIN).exists():
            membership = user.organization_memberships.filter(role=Membership.Role.ADMIN).select_related("organization").first()
            if membership and membership.organization:
                payout_profile = membership.organization
                stripe_account_id = getattr(membership.organization, "stripe_account_id", None)
                account_type = "organization"
                
        
        # instructor profile check
        if hasattr(user, "instructor") and user.instructor:
            payout_profile = user.instructor
            stripe_account_id = getattr(user.instructor, "stripe_account_id", None)
            account_type = "instructor"

        # affiliate profile check
        elif hasattr(user, "affiliate_profile") and user.affiliate_profile:
            payout_profile = user.affiliate_profile
            stripe_account_id = getattr(user.affiliate_profile, "stripe_account_id", None)
            account_type = "affiliate"

        if not payout_profile:
            return APIResponse.error(
                message="No payout profile found for this user.",
                status_code=400
            )

        if not stripe_account_id:
            return APIResponse.error(
                message=f"{account_type.capitalize()} Stripe account is not connected.",
                status_code=400
            )

        # rejected flow
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
                    "account_type": account_type,
                },
                status_code=200
            )

        # completed flow
        try:
            # 1. Transfer funds from Platform balance to Instructor's Stripe Balance
            transfer = stripe.Transfer.create(
                amount=int(withdrawal.amount * 100),
                currency="eur",
                destination=stripe_account_id
            )

            stripe_payout_id = None
            try:
                payout = stripe.Payout.create(
                    amount=int(withdrawal.amount * 100),
                    currency="eur",
                    stripe_account=stripe_account_id
                )
                stripe_payout_id = payout.id
            except Exception as e:
                # We log it, but don't fail the whole request because the Transfer was successful
                print(f"Automatic bank payout failed: {str(e)}")

            withdrawal.status = "approved"
            withdrawal.stripe_transfer_id = transfer.id
            withdrawal.stripe_payout_id = stripe_payout_id
            withdrawal.failure_reason = None
            withdrawal.save(update_fields=[
                "status",
                "stripe_transfer_id",
                "stripe_payout_id",
                "failure_reason",
                "updated_at"
            ])

            if account_type == "organization":
                payout_profile.current_balance -= withdrawal.amount
                payout_profile.total_withdrawals += withdrawal.amount
                payout_profile.save(update_fields=["current_balance", "total_withdrawals"])
                
            # Update payout profile balances
            if account_type == "instructor":
                payout_profile.current_balance -= withdrawal.amo
                payout_profile.total_withdrawals += withdrawal.amount
                payout_profile.save(update_fields=["current_balance", "total_withdrawals"])
                
            elif account_type == "affiliate":
                payout_profile.total_paid += withdrawal.amount
                payout_profile.save(update_fields=["total_paid"])
                
                # Mark all approved commissions for this affiliate as 'paid'
                payout_profile.commissions_records.filter(
                    status="approved"
                ).update(status="paid")

            return APIResponse.success(
                message="Withdrawal approved and paid successfully.",
                data={
                    "withdraw_id": withdrawal.withdraw_id,
                    "status": withdrawal.status,
                    "transfer_id": transfer.id,
                    "account_type": account_type,
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
    permission_classes = [IsAuthenticated, IsInstructor, IsOrganization]  # Allow both Instructors and Organization Admins to cancel their own withdrawals

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
        
        
        
        
        
# Affiliate Commission withdrawal view 


class AffiliateCreateStripeConnectAccountView(APIView):
    permission_classes = [IsAuthenticated, IsAffiliate]

    def post(self, request):
        user = request.user
        affiliate = user.affiliate_profile   

        try:
           
            if not affiliate.stripe_account_id:
                account = stripe.Account.create(
                    type="express",
                    country="IE",  # Ireland for Euro based accounts
                    email=user.email,
                    capabilities={
                        "transfers": {"requested": True},
                        "card_payments": {"requested": True},
                    },
                )

                affiliate.stripe_account_id = account.id
                affiliate.save(update_fields=["stripe_account_id"])

            else:
                account = stripe.Account.retrieve(affiliate.stripe_account_id)

            # return_url = request.build_absolute_uri(reverse("stripe-return-page"))
            # refresh_url = request.build_absolute_uri(reverse("stripe-cancel"))
            return_url = f"{settings.FONTEND_ULR}/en/affiliate/withdrawal"
            refresh_url = "http://localhost:8000/api/stripe/cancel"

            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type="account_onboarding",
            )

            details_submitted = getattr(account, "details_submitted", False)
            if details_submitted and not affiliate.stripe_onboarding_completed:
                affiliate.stripe_onboarding_completed = True
                affiliate.save(update_fields=["stripe_onboarding_completed"])

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
            
            
            
class AffiliateStripeDashboardLoginLinkView(APIView):
    permission_classes = [IsAuthenticated, IsAffiliate]

    def post(self, request):
        user = request.user
        
        try:
            affiliate = user.affiliate_profile
        except Affiliate.DoesNotExist:
            return APIResponse.error(
                message="You do not have an affiliate profile.",
                status_code=403
            )

        if not affiliate.stripe_account_id:
            return APIResponse.error(
                message="Stripe account not connected.",
                status_code=400
            )

        try:
            login_link = stripe.Account.create_login_link(affiliate.stripe_account_id)
            return APIResponse.success(
                message="Login link created successfully",
                data={"url": login_link.url}
            )
        except stripe.error.StripeError as e:
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=400
            )
            
            
            
           
class AffiliateWithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated, IsAffiliate]

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
        total_earnings = AffiliateCommission.objects.filter(
            affiliate=user.affiliate_profile
        ).aggregate(total=Sum("commission_rate"))["total"] or Decimal("0.00")
        
        print(f"Total Earnings*******: {total_earnings}")
        
        #  Already withdrawn
        withdrawn_amount = Withdrawal.objects.filter(
            user=user,
            status__in=["pending", "completed"]
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        
        print(f"Withdrawn Amount*******: {withdrawn_amount}")
        
        available_balance = total_earnings - withdrawn_amount
        print(f"Available Balance*******: {available_balance}")
        if amount > available_balance:
            return APIResponse.error(
                f"Insufficient balance. Available: {available_balance}", 400
            )

        #  Stripe account check
        affiliate = user.affiliate_profile
        if not affiliate.stripe_account_id:
            return APIResponse.error("Stripe account not connected", 400)

        try:
            account = stripe.Account.retrieve(affiliate.stripe_account_id)
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
        
        
        
        
# Withdrawal views for Organizations 
class OrganizationCreateStripeConnectAccountView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    def post(self, request):
        user = request.user
        membership = Membership.objects.filter(
            user=user, 
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).first()
        
        if not membership:
            return APIResponse.error("Organization account not found or unauthorized.", 404)
            
        organization = membership.organization

        try:
           
            if not organization.stripe_account_id:
                account = stripe.Account.create(
                    type="express",
                    country="IE",  # Ireland for Euro based accounts
                    email=user.email,
                    capabilities={
                        "transfers": {"requested": True},
                        "card_payments": {"requested": True},
                    },
                )

                organization.stripe_account_id = account.id
                organization.save(update_fields=["stripe_account_id"])

            else:
                account = stripe.Account.retrieve(organization.stripe_account_id)

            return_url = request.build_absolute_uri(reverse("stripe-return-page"))
            refresh_url = request.build_absolute_uri(reverse("stripe-cancel"))

            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type="account_onboarding",
            )

            details_submitted = getattr(account, "details_submitted", False)
            if details_submitted and not organization.stripe_onboarding_completed:
                organization.stripe_onboarding_completed = True
                organization.save(update_fields=["stripe_onboarding_completed"])

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
            
            
            
            
class OrganizationStripeDashboardLoginLinkView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    def post(self, request):
        user = request.user
        membership = Membership.objects.filter(
            user=user, 
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).first()
        
        if not membership:
            return APIResponse.error("Organization account not found or unauthorized.", 404)
            
        organization = membership.organization

        if not organization.stripe_account_id:
            return APIResponse.error(
                message="Stripe account not connected.",
                status_code=400
            )

        try:
            login_link = stripe.Account.create_login_link(organization.stripe_account_id)
            return APIResponse.success(
                message="Login link created successfully",
                data={"url": login_link.url}
            )
        except stripe.error.StripeError as e:
            return APIResponse.error(
                message=f"Stripe error: {str(e)}",
                status_code=400
            )
            
class  OrganizationWithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated, IsOrganization]

    @transaction.atomic
    def post(self, request):
        user = request.user
        membership = Membership.objects.filter(
            user=user, 
            role__in=[Membership.Role.ADMIN, Membership.Role.ADMIN]
        ).first()
        
        if not membership:
            return APIResponse.error("Organization account not found or unauthorized.", 404)
            
        organization = membership.organization
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

        #  Total earnings (from all organization courses)
        total_earnings = Commission.objects.filter(
            course__organization=organization
        ).aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")
        
        print(f"Total Earnings*******: {total_earnings}")
        
        #  Already withdrawn
        withdrawn_amount = Withdrawal.objects.filter(
            user=user,
            status__in=["pending", "completed"]
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        
        print(f"Withdrawn Amount*******: {withdrawn_amount}")
        
        available_balance = total_earnings - withdrawn_amount
        print(f"Available Balance*******: {available_balance}")
        if amount > available_balance:
            return APIResponse.error(
                f"Insufficient balance. Available: {available_balance}", 400
            )

        #  Stripe account check
        if not organization.stripe_account_id:
            return APIResponse.error("Stripe account not connected", 400)

        try:
            account = stripe.Account.retrieve(organization.stripe_account_id)
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
        
    
## This method can be called from the Enrollment model when a course is purchased to send notifications to the student, instructor, and organization admin (if applicable).if needed then integrated    
def notify_course_purchase(self, enrollment):
    student = enrollment.student
    course = enrollment.course

    # 1️⃣ Notify Student
    Notification.objects.create(
        user=student.user,
        type="purchase",
        title="Purchase Successful",
        body=f"You have successfully purchased the course: {course.title}"
    )

    # 2️⃣ Notify Instructor
    if course.instructor and course.instructor.user:
        Notification.objects.create(
            user=course.instructor.user,
            type="purchase",
            title="New Course Purchase",
            body=f"Your course '{course.title}' was purchased by {student.user.username}"
        )

    # 3️⃣ Notify Organization Admin (if exists)
    if course.organization:
        admin_members = course.organization.memberships.filter(
            role="ADMIN"
        ).select_related("user")

        for member in admin_members:
            Notification.objects.create(
                user=member.user,
                type="purchase",
                title="Course Revenue Generated",
                body=f"Your organization course '{course.title}' was purchased."
            )