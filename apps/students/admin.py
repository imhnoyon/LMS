from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'first_name', 'last_name', 'date_of_birth','gender','bio','profile_photo')
    search_fields = ('first_name', 'last_name', 'user__full_name')