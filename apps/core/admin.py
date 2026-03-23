from django.contrib import admin
from .models import Contact, FAQCategory, FAQ, SiteConfig



# Register your models here.
@admin.register(Contact)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'subject')
    
    
    
@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    
    
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('question',)
    
    
@admin.register(SiteConfig)
class PlatformConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'currency')
    search_fields = ('name',)
    
    