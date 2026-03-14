from django.db import models
from users.models import User


class Affiliate(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="affiliate_profile")
    
    referral_code = models.CharField(max_length=50, unique=True)
    commission_rate = models.DecimalField(max_digits=5,decimal_places=2)  
    total_earnings = models.DecimalField(max_digits=12,decimal_places=2,default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - Affiliate"
    
 
 
 
"""
Written by Mahedi Hasan Noyon
"""