from django.urls import path
from apps.messaging import views


# Messaging app URLs
urlpatterns = [
	path('conversations/', views.ConversationListCreateAPIView.as_view(), name='conversations-list-create'),
	path('conversations/<int:conversation_id>/messages/', views.MessageListCreateAPIView.as_view(), name='conversation-messages'),
]