from django.contrib import admin
from .models import Notification
# Register your models here.

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id','title','user', 'body', 'type','is_read', 'created_at')
    search_fields = ('title',)
    ordering = ('-created_at',)