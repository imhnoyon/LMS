from django.contrib import admin
from .models import Chat, Conversation,Message,Session

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display =('id','created_at','updated_at')
    search_fields = ('participants__username',)
    
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display =('id','conversation','sender','body','status','is_read','created_at')
    search_fields = ('status',)
    ordering = ('-created_at',)
    
    
    
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display =('session_id','user','course','created_at','updated_at')
    search_fields = ('session_id',)
    ordering = ('-created_at',)
    
    
    
@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display =('id','session','sender','body','created_at')
    search_fields = ('sender',)
    ordering = ('-created_at',)