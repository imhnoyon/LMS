from django.contrib import admin
from apps.affiliates.models import *


# Register your models here.

@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'iban','address','status', 'created_at')
    search_fields = ('user__username', 'iban')
    list_filter = ('created_at',)
    
    
    

@admin.register(AffiliateCourseLink)
class AffiliateCourseLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'affiliate', 'course', 'code', 'clicks','referral_url', 'unique_clicks', 'created_at')
    search_fields = ('affiliate__user__username', 'course__title', 'code')
    list_filter = ('created_at',)
    
    
@admin.register(AffiliateCommission)
class AffiliateCommissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'affiliate', 'product', 'commission_rate', 'created_at')
    search_fields = ('affiliate__user__username', 'product__title')
    list_filter = ('created_at',)
    
    
@admin.register(AffiliateReferralClick)
class AffiliateReferralClickAdmin(admin.ModelAdmin):
    list_display = ('id', 'affiliate', 'course', 'code', 'session_key', 'ip_address', 'clicked_at')
    search_fields = ('affiliate__user__name', 'course__title', 'code')
    list_filter = ('clicked_at',)