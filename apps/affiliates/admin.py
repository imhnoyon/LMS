from django.contrib import admin
from .models import Affiliate, AffiliateCommission
# Register your models here.

@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "affiliate_type", "status", "created_at")
    search_fields = ("user__email", "company_name")
    list_filter = ("affiliate_type", "status")
    
    
@admin.register(AffiliateCommission)
class AffiliateCommissionAdmin(admin.ModelAdmin):
    list_display = ("affiliate", "product", "commission_rate", "created_at")
    search_fields = ("affiliate__user__email", "product__title")
    list_filter = ("created_at",)
    
