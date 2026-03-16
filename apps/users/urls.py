from django.urls import path
from apps.users.views import *


# Users app URLs
urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="user-register"),
]