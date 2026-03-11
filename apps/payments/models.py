from django.db import models
from users.models import User
from orders.models import Order


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
        ("sslcommerz", "SSLCommerz"),
        ("paypal", "PayPal"),
        ("bkash", "Bkash"),
        ("nagad", "Nagad"),
        ("manual", "Manual"),
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
