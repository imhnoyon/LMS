from datetime import timedelta, timezone
import uuid
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework import status
from apps.organizations.models import Invitation, Organization, User
from apps.organizations.serializers import OrganizationRegisterSerializer
from apps.instructors.serializers import InstructorRegisterSerializer   
from apps.students.serializers import LearnerRegisterSerializer
from apps.affiliates.serializers import AffiliateRegisterSerializer
from apps.users.serializers import *
from utils.api_response import APIResponse
from .models import OTP
from utils.emails import *
from django.db.models import Q
from utils.paginations import CustomPagination
from django.core.mail import EmailMultiAlternatives 


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
        elif register_type == "affiliate":
            serializer = AffiliateRegisterSerializer(data=request.data)
        else:
            return APIResponse.error(message="Invalid registration type.",status_code=status.HTTP_400_BAD_REQUEST)
        
        if not serializer.is_valid():
            return APIResponse.error(errors=serializer.errors,status_code=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        
        # For verification email
        code = generate_otp()
        OTP.objects.create(
            user=user,
            code=code,
            expires_at=otp_expiry(),
            purpose="verify"
        )
        if user.email:
            send_verification_email(user.email, code)
       
        return APIResponse.success(
            message="Registration completed successfully.OTP sent to your email for verification.",
            data={"id": str(user.id)},
            status_code=status.HTTP_201_CREATED
        )
        
        
        
# Resend OTP for email verification and password reset 
class ResendVerificationCodeView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return APIResponse.error(message="Email is required", status_code=400)
        user = get_object_or_404(User, email=email)
        code = generate_otp()
        expires = otp_expiry()
        OTP.objects.filter(user=user, purpose="verify").delete()
        OTP.objects.create(user=user,code=code,expires_at=expires,purpose="verify")
        
        if user.email:
            send_verification_email(user.email, code)  
        return APIResponse.success(
            message="Resend code sent successfully. Please check your email!",
            data={
                "email": user.email,
                "expires_at": int(expires.timestamp() * 1000)
            }
        )
 
        
# Email Verification views 
class VerifyEmailView(APIView):
    def post(self, request):
        user = get_object_or_404(User, id=request.data.get("user_id"))
        Code = request.data.get("code")
        record = OTP.objects.filter(user=user, code=Code, purpose="verify", expires_at__gte=timezone.now()).first()
        if not record:
            return APIResponse.error(message="Invalid code", status_code=status.HTTP_400_BAD_REQUEST)
        user.is_verified = True
        user.save()
        record.delete()
        tokens = generate_tokens(user)
        return APIResponse.success(
            message="Email Verification Successfully!",
            data={
                **tokens,
                "user_id": str(user.id),
            },
            status_code=status.HTTP_200_OK
        )
     
        
# Signin view for all user role 
from django.contrib.auth.models import update_last_login
class SignInView(APIView):
    def post(self, request):
        password = request.data.get("password")
        user = User.objects.filter(
            email=request.data.get("email")).first()
        if not user or not user.check_password(password):
            return APIResponse.error(message="Invalid credentials", status_code=status.HTTP_400_BAD_REQUEST)

        # last_login update
        update_last_login(None, user)
        tokens = generate_tokens(user)

        return APIResponse.success(
            message="Login successful",
            data={
                **tokens,
                 "role": user.role,
                "user_id": str(user.id),
               
            }
        )  
        
class ForgotPasswordView(APIView):
    def post(self, request):
        user = User.objects.filter(
            email=request.data.get("email")
        ).first()

        if not user:
            return APIResponse.error(message="User not found", status_code=status.HTTP_404_NOT_FOUND)
        code = generate_otp()
        expires = otp_expiry()
        OTP.objects.create( user=user, code=code, expires_at=expires, purpose="reset")
        if user.email:
            send_reset_password_email(user.email,code)   
        return APIResponse.success(
            message="Reset password code sent successfully.please check your email!",
            data={
                "user_id": str(user.id),
                "expires_at": int(expires.timestamp() * 1000)
            }
        )
        
        
class VerifyResetCodeView(APIView):
    def post(self, request):
        user = get_object_or_404(User, id=request.data.get("user_id"))
        record = OTP.objects.filter(user=user,code=request.data.get("code"),purpose="reset",expires_at__gte=timezone.now()).first()
        if not record:
            return APIResponse.error(message="Invalid code", status_code=status.HTTP_400_BAD_REQUEST)
        secret_key = str(uuid.uuid4())
        record.code = secret_key
        record.save()
        return APIResponse.success(
            message="Code verified successfully",
            data={"secret_key": secret_key,"user_id":user.id}
        )
        
        
# Reset password view 
class ResetPasswordView(APIView):
    def post(self, request):
        user = get_object_or_404(User, id=request.data.get("user_id"))
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        if new_password != confirm_password:
            return APIResponse.error(message="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST)
        
        record = OTP.objects.filter(user=user,code=request.data.get("secret_key"),purpose="reset").first()
        if not record:
            return APIResponse.error(message="Invalid request", status_code=status.HTTP_400_BAD_REQUEST)
        # Update and save
        user.set_password(new_password)
        user.save()
        record.delete()
        return APIResponse.success(message="Password Reset Successful!", status_code=status.HTTP_200_OK)
    
    
    
#Custom token refresh view to refresh access token using refresh token
class CustomTokenRefreshView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return APIResponse.error(message="Refresh token required", status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)
            return APIResponse.success(
                message="Token refreshed successfully",
                data={"access_token": new_access}
            )
        except Exception as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        
        
        
class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination
    
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role")
        is_active = request.query_params.get("is_active")

        users = User.objects.all().exclude(is_staff=True)

        #search (name + email)
        if search:
            users = users.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search)
            )

        # role filter
        if role:
            users = users.filter(role=role)

        # active filter
        if is_active is not None:
            if is_active.lower() == "true":
                users = users.filter(is_active=True)
            elif is_active.lower() == "false":
                users = users.filter(is_active=False)

        users = users.order_by("-created_at")

        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request, view=self)
        serializer = UserListSerializer(paginated_users, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="User list retrieved successfully."
        )
        
# User detail view for admin panel with last active time       
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserDetailSerializer(user)
        return APIResponse.success(
            message="User details retrieved successfully.",
            data=serializer.data,
            status_code=200
        )
        
        
 # View for sending emails from admin panel to users      
class SendEmailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = SendEmailSerializer(data=request.data)

        if not serializer.is_valid():
            return APIResponse.error(
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        to_email = serializer.validated_data["to_email"]
        subject = serializer.validated_data["subject"]
        message = serializer.validated_data["message"]
        user=User.objects.filter(email=to_email).first()
        try:
            context = {
                "subject": subject,
                "message": message,
                "app_name": "Learn Hub",
                "recipient_name": user.name if user else "User",
                "button_url": None,
                "button_text": None,
            }

            html_content = render_to_string("emails/send_email.html", context)

            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            return APIResponse.success(
                message="Email sent successfully",
                data={
                    "to_email": to_email,
                    "subject": subject,
                    "message": message,
                },
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return APIResponse.error(
                message=f"Email sending failed: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )