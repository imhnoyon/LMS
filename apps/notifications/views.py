from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer

# Create your views here.
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user,is_read=False).order_by('-created_at')

        serializer = NotificationSerializer(notifications, many=True)

        return Response({
            "success": True,
            "status": 200,
            "message": "Notifications fetched successfully.",
            "data": serializer.data
        }, status=200)
        
    
class NotificationDetailView(APIView):
    def get(self, request,pk):
        notification = Notification.objects.filter(user=request.user, id=pk).first()
        if not notification:
            return Response({
                "success": False,
                "status": 404,
                "message": "Notification not found."
            }, status=404)

        notification.is_read = True
        notification.save()

        serializer = NotificationSerializer(notification)

        return Response({
            "success": True,
            "status": 200,
            "message": "Notification marked as read.",
            "data": serializer.data
        }, status=200)
        