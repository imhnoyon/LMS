from django.contrib import admin
from .models import AIChatConversation, AIChatMessage
# Register your models here.

@admin.register(AIChatConversation)
class AIChatConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "title", "created_at", "updated_at")
    list_filter = ("course", "created_at", "updated_at")
    search_fields = ("title", "user__username", "course__title")
    
    
@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "conversation__title", "conversation__user__username", "conversation__course__title")