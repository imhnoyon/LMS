from django.urls import path
from apps.notifications import views


# Notifications app URLs
urlpatterns = [
     path('notifications/',views.NotificationListView.as_view(),name='notification-list'),
     path('notifications/<int:pk>/',views.NotificationDetailView.as_view(),name='notification-detail'),
]