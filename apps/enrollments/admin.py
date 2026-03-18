from django.contrib import admin
from .models import Enrollment,Certificate
# Register your models here.

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "is_active", "is_completed",'order', "enrolled_at")
    list_filter = ("is_active", "is_completed", "enrolled_at")
    search_fields = ("user__username", "course__title")
    
    
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "course_title", "certificate_id", "issue_date")
    search_fields = ("enrollment__user__username", "enrollment__course__title", "certificate_id")
    