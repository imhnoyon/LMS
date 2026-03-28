from django.contrib import admin
from apps.instructors.models import *


# Register your models here.
@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    is_approved = models.BooleanField(default=False)
    list_display = ('id','user',  'title', 'biography','website', 'twitter', 'linkedin', 'youtube', 'current_balance', 'total_withdrawals', 'is_approved', 'is_featured', 'created_at')
    search_fields = ( 'id',)