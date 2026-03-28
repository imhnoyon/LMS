from django.contrib import admin
from apps.affiliates.models import Affiliate


# Register your models here.

@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'iban','address','status', 'created_at')
    search_fields = ('user__username', 'iban')
    list_filter = ('created_at',)
