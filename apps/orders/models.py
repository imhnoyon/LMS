from django.db import models
from users.models import User
from decimal import Decimal
from courses.models import Course

# Order model ------
class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
     )

    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="orders")
    order_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=150, blank=True, null=True)
    billing_email = models.EmailField(blank=True, null=True)
    billing_name = models.CharField(max_length=255, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_id"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def calculate_totals(self):
        subtotal = sum(
            [item.price for item in self.items.all()],
            Decimal("0.00")
        )
        self.subtotal = subtotal
        self.total_amount = subtotal - self.discount_amount
        self.save(update_fields=["subtotal", "total_amount"])
        
    def __str__(self):
        return f"{self.order_id} - {self.user}"

    
        
# Order Course item model ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="order_items")

    price = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["order", "course"]

    def __str__(self):
        return f"{self.order.order_id} - {self.course.title}"
    

# Wishlist model ----
class Wishlist(models.Model):
    user = models.ForeignKey( User, on_delete=models.CASCADE,related_name="wishlists")
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "course"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.course}"
    
    
# Student Enrollment model ----  
class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    is_active = models.BooleanField(default=True)
    
    enrolled_at = models.DateTimeField(auto_now_add=False)

    class Meta:
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user} - {self.course.title}"
    
#Purchase History Model ------    
class PurchaseHistory(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="purchase_histories")
    course = models.ForeignKey(Course, on_delete=models.CASCADE,related_name="purchases")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL,null=True,blank=True,related_name="purchase_histories")
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=150, blank=True, null=True)

    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "course"]
        ordering = ["-purchased_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["course"]),
            models.Index(fields=["purchased_at"]),
        ]

    def __str__(self):
        return f"{self.user} purchased {self.course}"    
 
 
    
    
"""
Written by Mahedi Hasan Noyon
"""