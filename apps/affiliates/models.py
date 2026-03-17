from django.db import models
from courses.models import Course
from users.models import User
from django.utils.crypto import get_random_string

class Affiliate(models.Model):
    AFFILIATE_TYPES = [
        ('partner', 'Partner'),
        ('external', 'External'),
        ('territorial', 'Territorial'),
      ]
    AFFILIATE_STATUS = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
      ] 
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="affiliate_profile")
    
    company_name = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    profile_photo = models.ImageField(upload_to='affiliate_photos/', blank=True, null=True)
    
    referral_code = models.CharField(max_length=50, unique=True)
    commission_rate = models.DecimalField(max_digits=5,decimal_places=2)  
    total_earnings = models.DecimalField(max_digits=12,decimal_places=2,default=0.00)
    
    is_active = models.BooleanField(default=True)
    affiliate_type = models.CharField(max_length=20, choices=AFFILIATE_TYPES, default='external')
    status = models.CharField(max_length=20, choices=AFFILIATE_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = get_random_string(10).upper()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.user} - Affiliate"



# Affiliate Commission Model
class AffiliateCommission(models.Model):
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE)
    product = models.ForeignKey(Course, on_delete=models.CASCADE)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    class Meta:
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.affiliate.user.email} - {self.commission_rate}"
    
    
    
    
    
    
"""
Written by Mahedi Hasan Noyon
"""