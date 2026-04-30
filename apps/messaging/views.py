from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from apps.messaging.models import Conversation, Message
from apps.messaging.serializers import ConversationSerializer, MessageSerializer
from apps.enrollments.models import Enrollment
from django.contrib.auth import get_user_model
from utils.api_response import APIResponse
User = get_user_model()


class ConversationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Student
        if getattr(user, 'role', None) == 'student':
            instructor_ids = Enrollment.objects.filter(user=user).values_list('course__instructor__id', flat=True).distinct()
            qs = Conversation.objects.filter(participants=user).filter(participants__in=instructor_ids).distinct().order_by("-updated_at")
        #  Instructor
        elif getattr(user, 'role', None) == 'instructor':
            student_ids = Enrollment.objects.filter(course__instructor=user).values_list('user__id', flat=True  ).distinct()
            qs = Conversation.objects.filter(participants=user).filter(participants__in=student_ids).distinct().order_by("-updated_at")
        else:
            qs = Conversation.objects.filter(participants=user).order_by("-updated_at")
        serializer = ConversationSerializer(qs, many=True, context={"request": request})
        return Response({
            "success": True,
            "data": serializer.data
        })

	

class MessageListCreateAPIView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, conversation_id):
		conv = get_object_or_404(Conversation, id=conversation_id)
		if not conv.participants.filter(id=request.user.id).exists():
			return Response({"success": False, "message": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
		msgs = conv.messages.order_by("created_at")
		serializer = MessageSerializer(msgs, many=True)
		return APIResponse.success("Messages retrieved successfully", serializer.data)

	
