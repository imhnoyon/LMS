from django.contrib import admin
from apps.organizations.models import *


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):  
    list_display = ("id", "name", "owner","bio","phone","rating","total_reviews","total_students","total_courses","is_active","is_verified","verified_by", "created_at")
    search_fields = ("name", )
    list_filter = ("created_at",)
    
@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "role", "status", "joined_at")
    search_fields = ("organization__name", "user__email")
    list_filter = ("role", "status", "joined_at")
    
@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "invited_by", "email", "role", "status", "created_at", "expires_at")
    search_fields = ("organization__name", "invited_by__email", "email")
    list_filter = ("role", "status", "created_at")
    

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("id", "instructor", "course", "revenue_share", "expiry_date", "status", "created_at")
    search_fields = ("organization__name", "instructor__email")
    list_filter = ("status", "created_at")