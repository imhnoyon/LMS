from django.contrib import admin
from .models import InstructorProfile
# Register your models here.


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin): 
    list_display = ('instructor_id', 'user', 'first_name', 'last_name', 'instructor_type', 'organization')
    search_fields = ('first_name', 'last_name', 'user__username')
    list_filter = ('instructor_type', )