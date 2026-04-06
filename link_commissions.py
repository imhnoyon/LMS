import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.affiliates.models import AffiliateCommission, AffiliateCourseLink
from apps.orders.models import OrderItem

def run():
    print("Linking commissions to orders...")
    commissions = AffiliateCommission.objects.filter(order__isnull=True)
    for comm in commissions:
        # Find which referral codes belong to this affiliate
        codes = AffiliateCourseLink.objects.filter(affiliate=comm.affiliate).values_list('code', flat=True)
        
        # Link this commission to the correct order item
        item = OrderItem.objects.filter(
            course=comm.product, 
            referral_code__in=codes
        ).first()
        
        if item:
            comm.order = item.order
            comm.save()
            print(f"Linked AffiliateCommission {comm.id} to Order {item.order.order_id}")
        else:
            print(f"No matching order item found for AffiliateCommission {comm.id}")

if __name__ == "__main__":
    run()
