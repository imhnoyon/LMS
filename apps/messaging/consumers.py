from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from apps.messaging.models import Conversation, Message
from apps.enrollments.models import Enrollment

User = get_user_model()


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
        self.group_name = f"conversation_{self.conversation_id}"

        user = self.scope.get('user')
        
        # If user not authenticated via middleware, try to get from query params
        if not user or not user.is_authenticated:
            token = self._get_token_from_query()
            if token:
                user = await database_sync_to_async(self._authenticate_token)(token)
        
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user = user

        # Verify conversation exists and user is a participant and purchase relationship holds
        conv = await database_sync_to_async(self._get_conversation)()
        if not conv:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Expecting {"type": "message", "body": "..."}
        msg_type = content.get('type')
        if msg_type != 'message':
            return
        body = content.get('body', '').strip()
        if not body:
            return

        # Create message in DB
        msg = await database_sync_to_async(self._create_message)(body)

        payload = {
            'type': 'chat.message',
            'id': str(msg.id),
            'conversation': str(self.conversation_id),
            'sender_id': str(msg.sender.name),
            'body': msg.body,
            'created_at': msg.created_at.isoformat(),
        }

        await self.channel_layer.group_send(self.group_name, payload)

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    # -- synchronous helpers run in threadpool --
    def _get_conversation(self):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            return None

        # must be participant
        if not conv.participants.filter(id=self.user.id).exists():
            return None

        # Check purchase relationship: there must be at least one enrollment where one participant is instructor and the other is student
        # find the other participant(s)
        others = conv.participants.exclude(id=self.user.id)
        if not others.exists():
            return None

        # For two-person chats, check enrollment either way
        for other in others:
            if Enrollment.objects.filter(user=self.user, course__instructor=other).exists():
                return conv
            if Enrollment.objects.filter(user=other, course__instructor=self.user).exists():
                return conv

        return None

    def _create_message(self, body):
        conv = Conversation.objects.get(id=self.conversation_id)
        # Create message as request user
        msg = Message.objects.create(conversation=conv, sender=self.user, body=body)
        return msg

    def _get_token_from_query(self):
        """Extract JWT token from query string"""
        query_string = self.scope.get('query_string', b'').decode()
        if not query_string:
            return None
        
        for param in query_string.split('&'):
            if param.startswith('token='):
                return param.split('=', 1)[1]
        
        return None

    def _authenticate_token(self, token):
        """Authenticate JWT token and return user"""
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.conf import settings
            
            # Decode the JWT token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # Get the user from database
            user = User.objects.get(id=user_id)
            return user
        except Exception as e:
            print(f"Token auth error: {e}")
            return None
