from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.messaging.models import Conversation, Message

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ["id", "name", "email", "avatar"]


class MessageSerializer(serializers.ModelSerializer):
	sender_name = serializers.CharField(source="sender.name", read_only=True)

	class Meta:
		model = Message
		fields = ["id", "conversation", "sender", "sender_name", "body", "status", "is_read", "created_at"]
		read_only_fields = ["id", "sender", "status", "is_read", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
	participants = UserMiniSerializer(many=True, read_only=True)
	last_message = serializers.SerializerMethodField()
	unread_count = serializers.SerializerMethodField()

	class Meta:
		model = Conversation
		fields = ["id", "participants", "created_at", "updated_at", "last_message", "unread_count"]

	def get_last_message(self, obj):
		last = obj.messages.order_by("-created_at").first()
		return last.body if last else None

	def get_unread_count(self, obj):
		request = self.context.get("request")
		if not request or not request.user.is_authenticated:
			return 0
		return obj.unread_count(request.user)
