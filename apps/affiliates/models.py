from rest_framework import status

from apps.courses.models import Course
from django.conf import settings
from django.db import models
import string
import random
import uuid
from django.utils.text import slugify
from apps.notifications.models import User
from utils.api_response import APIResponse


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

    iban = models.CharField(max_length=34, blank=True,null=True)
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
    
    
    
# Affiliate Course Link Model
class AffiliateCourseLink(models.Model):
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE, related_name="course_links")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="affiliate_links")

    code = models.CharField(max_length=50, unique=True, db_index=True)
    referral_url = models.URLField(blank=True, null=True)

    clicks = models.PositiveIntegerField(default=0)
    unique_clicks = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("affiliate", "course")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.affiliate.user.name} -> {self.course.title}"

    def save(self, *args, **kwargs):
        if not self.code:
            base = slugify(self.course.title)[:20]
            self.code = f"{self.affiliate.id}-{base}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
 
 
 
 
class AffiliateReferralClick(models.Model):
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE, related_name="referral_clicks")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="referral_clicks")
    affiliate_link = models.ForeignKey(AffiliateCourseLink, on_delete=models.CASCADE, related_name="click_logs")

    code = models.CharField(max_length=50, db_index=True)
    session_key = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    clicked_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="affiliate_clicks")

    is_converted = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-clicked_at"]