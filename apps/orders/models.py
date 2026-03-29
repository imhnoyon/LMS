from django.db import models
from apps.users.models import User
from decimal import Decimal
from apps.courses.models import Course
from django.utils import timezone
import random
import string


# Create your models here.
class Coupon(models.Model):
    TYPE_CHOICES = (
        ("percent", "Percentage"),
        ("flat", "Flat Amount"),
    )

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="percent")
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)  # 8% or $10
    max_uses = models.PositiveIntegerField(default=0)   # 0 = unlimited
    used_count = models.PositiveIntegerField(default=0)
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            (self.max_uses == 0 or self.used_count < self.max_uses)
        )

    def __str__(self):
        return f"{self.code} - {self.discount_value}"
    
    
def generate_order_id():
    date_part = timezone.now().strftime("%Y%b").upper()
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{date_part}-{random_part}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.name
    
    
class CartItems(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_products')
    course_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cart.user.name} - {self.course.title}"

class Order(models.Model):
    STATUS_CHOICES = (
        ("pending",   "Pending"),
        ("paid",      "Paid"),
        ("failed",    "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded",  "Refunded"),
    )

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    order_id    = models.CharField(max_length=50, unique=True, blank=True)
    coupon      = models.ForeignKey(Coupon, on_delete=models.SET_NULL,null=True, blank=True, related_name="orders")
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_id"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    # ── Auto generate order_id ──
    def save(self, *args, **kwargs):
        if not self.order_id:
            order_id = generate_order_id()
            while Order.objects.filter(order_id=order_id).exists():
                order_id = generate_order_id()
            self.order_id = order_id
        super().save(*args, **kwargs)

    # ── Calculate subtotal & total ──
    def calculate_totals(self):
        self.subtotal = sum(
            (item.paid_price for item in self.items.all()),
            Decimal("0.00")
        )
        self.total_amount = self.subtotal - self.discount_amount
        self.save(update_fields=["subtotal", "total_amount"])

    # ── Coupon apply ──
    def apply_coupon(self, coupon):
        if not coupon.is_valid():
            raise ValueError("Coupon is not valid")
        if coupon.discount_type == "percent":
            self.discount_amount = (self.subtotal * coupon.discount_value) / Decimal("100")
        else:
            self.discount_amount = coupon.discount_value
        self.coupon = coupon
        self.total_amount = self.subtotal - self.discount_amount
        self.save(update_fields=["coupon", "discount_amount", "total_amount"])

    def __str__(self):
        return f"{self.order_id} - {self.user}"


class OrderItem(models.Model):
    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    course         = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="order_items")
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    paid_price     = models.DecimalField(max_digits=10, decimal_places=2)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("order", "course")

    def __str__(self):
        return f"{self.order.order_id} - {self.course.title}"

    

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name}'s Wishlist"

    def get_total_items(self):
        return self.items.count()

    def get_total_price(self):
        return sum(item.course.discounted_price or item.course.original_price 
                   for item in self.items.select_related('course'))


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'course')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.wishlist.user.name} → {self.course.title}"