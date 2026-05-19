from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/messaging/conversations/(?P<conversation_id>[^/]+)/$", consumers.ConversationConsumer.as_asgi()),
]
