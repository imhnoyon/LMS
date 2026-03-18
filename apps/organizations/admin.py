from django.contrib import admin
from .models import Organization, Team, MemberInvitation, RolePermission,Contract


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):  
    list_display = ("id", "name", "owner","bio","phone","email","rating","total_reviews","total_students","total_courses","is_active","is_verified","verified_by", "created_at")
    search_fields = ("name", "email")
    list_filter = ("created_at",)