from apps.courses.models import Course
from django.conf import settings
from django.db import models
import string
import random
import uuid


# Create your models here.
def generate_affiliate_id():
    max_attempts = 10
    for _ in range(max_attempts):
        new_id = 'AFF-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Affiliate.objects.filter(id=new_id).exists():
            return new_id
    return 'AFF-' + str(uuid.uuid4()).upper().replace('-', '')[:6]


class Affiliate(models.Model):
    AFFILIATE_TYPE_CHOICES = [
        ("affiliate", "Affiliate"),
        ("external_affiliate", "External Affiliate"),
        ("territorial_orientation_center", "Territorial Orientation Center"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
        ("pending", "Pending"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=20,
        editable=False,
        default=generate_affiliate_id,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="affiliate_profile",
        limit_choices_to={"role": "affiliate"},
    )

    affiliate_type = models.CharField(
        max_length=50,
        choices=AFFILIATE_TYPE_CHOICES,
        default="affiliate",
    )

    iban = models.CharField(max_length=34)
    tax_id = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)

    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    @property
    def total_payable(self):
        return self.total_earned - self.total_paid

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.id}"


# Affiliate Commission Model
class AffiliateCommission(models.Model):
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE)
    product = models.ForeignKey(Course, on_delete=models.CASCADE)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.affiliate.user.email} - {self.commission_rate}"