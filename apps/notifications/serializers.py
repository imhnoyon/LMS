from rest_framework import serializers
from apps.notifications.models import *


# Notifications app serializers

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'body', 'is_read', 'created_at']
        
        