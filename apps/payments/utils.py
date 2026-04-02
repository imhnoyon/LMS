from decimal import Decimal
from django.db.models import Sum
from apps.payments.models import Commission, Withdrawal
import stripe
from apps.courses.models import Course


def retrieve_connected_account(user):
    if not user.stripe_account_id:
        return None
    return stripe.Account.retrieve(user.stripe_account_id)


def refresh_stripe_account_status(user):
    """
    Returns latest Stripe account object for the connected account.
    """
    try:
        if not user.stripe_account_id:
            return None

        account = stripe.Account.retrieve(user.stripe_account_id)
        return {
            "account": account,
            "charges_enabled": account.get("charges_enabled", False),
            "payouts_enabled": account.get("payouts_enabled", False),
            "details_submitted": account.get("details_submitted", False),
        }
    except Exception as e:
        print(f"Stripe sync error: {e}")
        return None
    

def get_creator_available_balance(user):
    total_commission = Course.objects.filter(
        instructor=user
    ).aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")

    total_withdrawn = Withdrawal.objects.filter(
        creator=user,
        status__in=["pending", "processing", "completed"]
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return total_commission - total_withdrawn