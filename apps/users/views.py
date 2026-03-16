from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from apps.organizations.serializers import OrganizationRegisterSerializer
from apps.instructors.serializers import InstructorRegisterSerializer   
from apps.students.serializers import LearnerRegisterSerializer
from apps.utils.responses import APIResponse
# Create your views here.

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        register_type = request.data.get("type")

        if register_type == "organization":
            serializer = OrganizationRegisterSerializer(data=request.data)
        elif register_type == "learner":
            serializer = LearnerRegisterSerializer(data=request.data)
        elif register_type == "instructor":
            serializer = InstructorRegisterSerializer(data=request.data)
        else:
            return APIResponse.error(
                message="Invalid registration type.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not serializer.is_valid():
            return APIResponse.error(
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        user = serializer.save()
        # For verification email, you would typically generate a code and send an email here.
        
        """"
        apply email sending logic here,
        code = generate_verification_code()
        """
        return APIResponse.success(
            message="Registration completed successfully.",
            data={"id": str(user.id)},
            status_code=status.HTTP_201_CREATED
        )