from django.contrib import admin
from .models import User,OTP
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "is_active","is_verified","is_staff", "created_at","signature_url")
    search_fields = ("name", "email")
    list_filter = ("role", "is_active", "is_verified")
    
    
@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "code", "expires_at", "purpose")
    search_fields = ("user__name", "user__email")
    list_filter = ("purpose", "expires_at")