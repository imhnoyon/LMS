from django.db import models
from apps.users.models import User
from apps.orders.models import Order
from django.utils import timezone
from apps.courses.models import Course


# Create your models here.
class Payment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
       
    )
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="payments")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending")
    transaction_id = models.CharField(max_length=150,unique=True, null=True,blank=True)
    gateway_payment_id = models.CharField(max_length=150,null=True,blank=True)
    currency = models.CharField(max_length=10, default="USD")
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["order"]),
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        return f"{self.order.order_id} - {self.status}"


class PaymentGateway(models.Model):
    GATEWAY_TYPES = [
        ('stripe',        'Stripe'),
        ('paypal',        'PayPal'),
        ('local_gateway', 'Local Gateway'),
    ]
    TARGET_CHOICES = [
        ('organizations', 'Organizations'),
        ('instructors',   'Instructors'),
        ('white_label',   'White Label'),
    ]
    name         = models.CharField(max_length=100)
    gateway_type = models.CharField(max_length=30, choices=GATEWAY_TYPES)
    target       = models.CharField(max_length=20, choices=TARGET_CHOICES)
    balance      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active    = models.BooleanField(default=True)
    last_checked = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f"{self.name} ({self.target})"
 
 
class Transaction(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending',   'Pending'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]
    METHOD_CHOICES = [
        ('stripe',        'Stripe'),
        ('paypal',        'PayPal'),
        ('local_gateway', 'Local Gateway'),
    ]
 
    transaction_id = models.CharField(max_length=20, unique=True, editable=False)
    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transactions')
    course         = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    gateway        = models.ForeignKey(PaymentGateway, on_delete=models.SET_NULL, null=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    currency       = models.CharField(max_length=3, default='USD')
    method         = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at     = models.DateField(auto_now_add=True)
 
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            last = Transaction.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.transaction_id = f"TXN-{next_id:06d}"
        super().save(*args, **kwargs)
 
    def __str__(self):
        return self.transaction_id
 
 
class RevenueDistribution(models.Model):
    """Platform-wide revenue split config."""
    platform_pct     = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    organization_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    instructor_pct   = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    effective_date   = models.DateField(auto_now_add=True)
 
    def __str__(self):
        return f"Split as of {self.effective_date}"
 
 
# ══════════════════════════════════════════════════════════════════
# PAYMENTS — INSTRUCTOR WALLET & WITHDRAWALS
# ══════════════════════════════════════════════════════════════════
 
class PaymentMethod(models.Model):
    METHOD_TYPES = [
        ('bank_transfer', 'Bank Transfer (IBAN)'),
        ('visa',          'Visa'),
        ('mastercard',    'Mastercard'),
        ('paypal',        'PayPal'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=30, choices=METHOD_TYPES)
    is_default  = models.BooleanField(default=False)
 
    # Bank Transfer
    iban        = models.CharField(max_length=34, blank=True, null=True)
 
    # Card
    card_last4  = models.CharField(max_length=4,   blank=True, null=True)
    card_expiry = models.CharField(max_length=5,   blank=True, null=True)  # MM/YY
    cardholder  = models.CharField(max_length=100, blank=True, null=True)
    card_brand  = models.CharField(max_length=20,  blank=True, null=True)
 
    created_at  = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-is_default', '-created_at']
 
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.method_type} — {self.user}"
 
 
class Wallet(models.Model):
    user              = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    current_balance   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    today_revenue     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at        = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f"{self.user} — ${self.current_balance}"
 
 
class Payout(models.Model):
    """Admin-triggered monthly payouts (Image 1 — PAY-YYYY-MM-NNN)."""
    STATUS_CHOICES = [
        ('paid',    'Paid'),
        ('pending', 'Pending'),
        ('failed',  'Failed'),
    ]
    payout_id      = models.CharField(max_length=20, unique=True, editable=False)
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    currency       = models.CharField(max_length=3, default='EUR')
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payout_date    = models.DateField()
    created_at     = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-payout_date']
 
    def save(self, *args, **kwargs):
        if not self.payout_id:
            now    = timezone.now()
            prefix = f"PAY-{now.year}-{now.month:02d}-"
            count  = Payout.objects.filter(payout_id__startswith=prefix).count() + 1
            self.payout_id = f"{prefix}{count:03d}"
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.payout_id} — {self.amount} {self.currency}"
 
 
class Withdrawal(models.Model):
    """User-triggered on-demand withdrawals (Image 2)."""
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    wallet         = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='withdrawals')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    currency       = models.CharField(max_length=3, default='USD')
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at   = models.DateTimeField(auto_now_add=True)
    completed_at   = models.DateTimeField(blank=True, null=True)
 
    class Meta:
        ordering = ['-requested_at']
 
    def __str__(self):
        return f"Withdrawal #{self.pk} — {self.amount} ({self.status})"
 
 
class DailyRevenueSnapshot(models.Model):
    """Powers the earnings statistics chart."""
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revenue_snapshots')
    date    = models.DateField()
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
 
    class Meta:
        unique_together = ('user', 'date')
        ordering = ['date']
        

"""
Written by Mahedi Hasan Noyon
"""