from django.contrib import admin
from .models import *



@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount','payment_method', 'currency', 'status','transaction_id','gateway_payment_id','paid_at', 'created_at')
    list_filter  = ('status', 'created_at')
    search_fields = ('user__full_name', 'payment_id')
    
    
@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ('name','gateway_type','target','balance','is_active','last_checked', )
    list_filter  = ('is_active', )
    search_fields = ('name',)
    
    
    
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user','course','transaction_id',  'amount', 'method', 'status', 'created_at')
    list_filter  = ('status', 'method', 'created_at')
    search_fields = ('transaction_id',)
    
    
@admin.register(RevenueDistribution)
class RevenueDistributionAdmin(admin.ModelAdmin):
    list_display = ('platform_pct', 'organization_pct', 'instructor_pct', 'effective_date')
    
    
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('name','invoice_id','payment_method', 'amount','currency', 'status','invoice_date', 'created_at')
    list_filter  = ('status', 'created_at')
    search_fields = ('user__full_name',)

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'course', 'order_amount', 'commission_amount', 'payment_method', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('user__name', 'course__title')