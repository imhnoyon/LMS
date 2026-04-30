from datetime import timedelta, timezone
import uuid
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework import status
from apps.courses.models import Course
from apps.organizations.models import Invitation, Organization, User
from apps.organizations.serializers import OrganizationRegisterSerializer
from apps.instructors.serializers import InstructorRegisterSerializer   
from apps.payments.models import Payment
from apps.students.serializers import LearnerRegisterSerializer
from apps.affiliates.serializers import AffiliateRegisterSerializer
from apps.users.serializers import *
from utils.api_response import APIResponse
from .models import OTP
from apps.affiliates.models import AffiliateReferralClick
from utils.emails import *
from django.db.models import Q, Sum
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
        
        # 🔗 Auto-associate existing Affiliate Clicks to this new User
        ip_address = request.META.get('REMOTE_ADDR')
        AffiliateReferralClick.objects.filter(
            ip_address=ip_address,
            clicked_by__isnull=True,
            is_converted=False
        ).update(clicked_by=user)
        
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

        # 🔗 Auto-associate existing Affiliate Clicks to this User on Login (IP Pairing)
        ip_address = request.META.get('REMOTE_ADDR')
        AffiliateReferralClick.objects.filter(
            ip_address=ip_address,
            clicked_by__isnull=True,
            is_converted=False
        ).update(clicked_by=user)

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
            
# View to block or unblock users from admin panel          
class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if request.user == user:
            return APIResponse.error(
                message="You cannot block or unblock yourself.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 🔁 Toggle logic
        if user.is_active:
            # 🔴 Block user
            user.is_active = False
            user.is_verified = False
            status_text = "blocked"
            message = "User blocked successfully."
        else:
            # 🟢 Unblock user
            user.is_active = True
            status_text = "unblocked"
            message = "User unblocked successfully."

        user.save(update_fields=["is_active", "is_verified"])

        return APIResponse.success(
            message=message,
            data={
                "user_id": str(user.id),
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "status": status_text
            },
            status_code=status.HTTP_200_OK
        )
        
        
        
# class UnblockUserView(APIView):
#     permission_classes = [IsAuthenticated, IsAdminUser]

#     def patch(self, request, pk):
#         user = get_object_or_404(User, pk=pk)

#         if request.user == user:
#             return APIResponse.error(
#                 message="You cannot unblock yourself.",
#                 status_code=status.HTTP_400_BAD_REQUEST
#             )

#         if not user.is_active:
#             user.is_active = True
#             user.is_verified = True
#             user.save(update_fields=["is_active","is_verified"])

#             return APIResponse.success(
#                 message="User unblocked successfully.",
#                 data={
#                     "user_id": str(user.id),
#                     "is_active": user.is_active,
#                     "is_verified": user.is_verified,
#                     "status": "unblocked"
#                 },
#                 status_code=status.HTTP_200_OK
#             )

#         return APIResponse.success(
#             message="User is already active.",
#             data={
#                 "user_id": str(user.id),
#                 "is_active": user.is_active,
#                 "is_verified": user.is_verified,
#                 "status": "already active"
#             },
#             status_code=status.HTTP_200_OK
#         )
        
        
        
class AdminDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # 📊 Top Metrics
        total_users = User.objects.exclude(is_staff=True).count()
        total_courses = Course.objects.count()
        total_revenue = Payment.objects.filter(status="success").aggregate(total=Sum("amount"))["total"] or 0

        # 📈 Trends (Compared to last month)
        last_month_users = User.objects.filter(created_at__range=[last_month_start, last_month_end]).count()
        user_trend = ((total_users - last_month_users) / last_month_users * 100) if last_month_users > 0 else 100

        last_month_revenue = Payment.objects.filter(
            status="success", paid_at__range=[last_month_start, last_month_end]
        ).aggregate(total=Sum("amount"))["total"] or 0
        revenue_trend = ((float(total_revenue) - float(last_month_revenue)) / float(last_month_revenue) * 100) if last_month_revenue > 0 else 100

        # ⚠️ Attention Required
        pending_courses = Course.objects.filter(status="published").count() # Assuming published means pending for now
        
        # 🕒 Recent Activity (Last 5 events)
        recent_users = User.objects.exclude(is_staff=True).order_by("-created_at")[:3]
        recent_courses = Course.objects.order_by("-created_at")[:3]
        
        activities = []
        for u in recent_users:
            activities.append({
                "type": "registration",
                "title": f"New {u.role} registered",
                "description": u.name or u.email,
                "timestamp": u.created_at,
                "status": "Success"
            })
        for c in recent_courses:
            activities.append({
                "type": "course_submission",
                "title": "Course submitted for review",
                "description": c.title,
                "timestamp": c.created_at,
                "status": "Pending"
            })
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        # 📅 Today's Stats
        from apps.enrollments.models import Enrollment
        new_users_today = User.objects.filter(created_at__date=today).count()
        enrollments_today = Enrollment.objects.filter(enrolled_at__date=today).count()
        revenue_today = Payment.objects.filter(status="success", paid_at__date=today).aggregate(total=Sum("amount"))["total"] or 0

        return APIResponse.success(
            message="Admin dashboard stats retrieved successfully.",
            data={
                "top_metrics": {
                    "total_users": {
                        "value": total_users,
                        "trend": f"+{user_trend:.1f}%" if user_trend >= 0 else f"{user_trend:.1f}%",
                        "description": "from last month"
                    },
                    "total_courses": {
                        "value": total_courses,
                        "pending": pending_courses,
                        "description": "pending review"
                    },
                    "platform_revenue": {
                        "value": float(total_revenue),
                        "trend": f"+{revenue_trend:.1f}%" if revenue_trend >= 0 else f"{revenue_trend:.1f}%",
                        "description": "from last month"
                    }
                },
                "attention_required": {
                    "pending_courses": pending_courses,
                    # "user_reports": 0, # Placeholder if no report model
                    "message": f"{pending_courses} courses pending review,"
                },
                "recent_activity": activities[:5],
                "today_stats": {
                    "new_users": new_users_today,
                    "course_enrollments": enrollments_today,
                    "revenue": float(revenue_today),
                    # "support_tickets": 0 # Placeholder
                }
            },
            status_code=status.HTTP_200_OK
        )
        
        
        
        
class AdminPaymentsDeshboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        from apps.payments.models import Payment, Withdrawal, Commission
        from django.db.models import Sum, Q
        
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # 💰 1. Top Cards
        # Total Revenue (MTD)
        mtd_revenue = Payment.objects.filter(status="success", paid_at__date__gte=first_of_month).aggregate(total=Sum("amount"))["total"] or 0
        last_month_revenue = Payment.objects.filter(status="success", paid_at__date__range=[last_month_start, last_month_end]).aggregate(total=Sum("amount"))["total"] or 0
        revenue_growth = ((float(mtd_revenue) - float(last_month_revenue)) / float(last_month_revenue) * 100) if last_month_revenue > 0 else 100

        # Pending Payouts
        pending_payouts = Withdrawal.objects.filter(status="pending").aggregate(total=Sum("amount"))["total"] or 0
        pending_payout_count = Withdrawal.objects.filter(status="pending").count()

        # Platform Earnings (Total Commission collected by Admin)
        platform_earnings = User.objects.aggregate(total=Sum("platform_revenue"))["total"] or 0

        # 📊 2. Revenue Distribution (Donut Chart)
        total_payouts = Commission.objects.aggregate(total=Sum("commission_amount"))["total"] or 0
        instructor_commissions = Commission.objects.filter(course__organization__isnull=True).aggregate(total=Sum("commission_amount"))["total"] or 0
        org_commissions = Commission.objects.filter(course__organization__isnull=False).aggregate(total=Sum("commission_amount"))["total"] or 0
        
        total_distributed = float(platform_earnings) + float(instructor_commissions) + float(org_commissions)
        distribution = {
            "platform": {"amount": float(platform_earnings), "percentage": round((float(platform_earnings)/total_distributed*100), 1) if total_distributed > 0 else 0},
            "organizations": {"amount": float(org_commissions), "percentage": round((float(org_commissions)/total_distributed*100), 1) if total_distributed > 0 else 0},
            "instructors": {"amount": float(instructor_commissions), "percentage": round((float(instructor_commissions)/total_distributed*100), 1) if total_distributed > 0 else 0},
        }

        # 🏦 3. Payment Gateway Status (Dynamic Data)
        org_pending_payouts = float(Withdrawal.objects.filter(status="pending", user__role__in=["Or_admin", "manager"]).aggregate(total=Sum("amount"))["total"] or 0)
        org_payout_count = Withdrawal.objects.filter(status="pending", user__role__in=["Or_admin", "manager"]).count()
        
        ins_pending_payouts = float(Withdrawal.objects.filter(status="pending", user__role="instructor").aggregate(total=Sum("amount"))["total"] or 0)
        ins_payout_count = Withdrawal.objects.filter(status="pending", user__role="instructor").count()
        
        stripe_volume_today = float(Payment.objects.filter(status="success", paid_at__date=today).aggregate(total=Sum("amount"))["total"] or 0)
        stripe_txn_today = Payment.objects.filter(status="success", paid_at__date=today).count()

        gateway_status = [
            {
                "name": "Organizations", 
                "status": "operational", 
                "message": f"{org_payout_count} pending payout requests" if org_payout_count > 0 else "All payouts cleared", 
                "amount": f"{org_pending_payouts:,.2f}"
            },
            {
                "name": "Instructors", 
                "status": "operational", 
                "message": f"{ins_payout_count} pending payout requests" if ins_payout_count > 0 else "All payouts cleared", 
                "amount": f"{ins_pending_payouts:,.2f}"
            },
            {
                "name": "Stripe Gateway", 
                "status": "operational", 
                "message": f"{stripe_txn_today} successful transactions today", 
                "amount": f"{stripe_volume_today:,.2f}"
            },
        ]

        # 📝 4. Payment Transactions History
        recent_payments = Payment.objects.select_related("user", "order").order_by("-created_at")[:10]
        transactions_history = []
        
        for p in recent_payments:
            # Fetch first course title from the related order items
            from apps.orders.models import OrderItem
            item = OrderItem.objects.filter(order=p.order).first()
            course_title = item.course.title if item and item.course else "Multiple Courses"

            transactions_history.append({
                "transaction_id": p.transaction_id or f"TXN-{str(p.id)[:8].upper()}",
                "user": {
                    "name": p.user.name or "Unknown",
                    "email": p.user.email,
                    "avatar": request.build_absolute_uri(p.user.avatar.url) if p.user.avatar else None
                },
                "course": course_title,
                "amount": float(p.amount),
                "method": p.payment_method or "stripe",
                "status": p.status,
                "date": p.paid_at.date() if p.paid_at else p.created_at.date()
            })

        return APIResponse.success(
            message="Admin analytics data retrieved successfully.",
            data={
                "top_metrics": {
                    "total_revenue": {
                        "value": float(mtd_revenue),
                        "trend": f"{revenue_growth:+.1f}%",
                        "description": "from last month"
                    },
                    "pending_payouts": {
                        "value": float(pending_payouts),
                        "count": pending_payout_count,
                        "description": "pending transfers"
                    },
                    "platform_earnings": {
                        "value": float(platform_earnings),
                        "commission_rate": "10% commission"
                    }
                },
                "revenue_distribution": distribution,
                "gateway_status": gateway_status,
                "transactions_history": transactions_history
            },
            status_code=status.HTTP_200_OK
        )

   
            
            
class AdminAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        from apps.payments.models import Payment
        from apps.courses.models import Course
        from apps.users.models import User
        from apps.enrollments.models import Enrollment
        from django.db.models import Sum, Count, Q
        from datetime import timedelta
        from django.utils import timezone

        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # 📊 1. Top Metrics with Trends
        total_users = User.objects.exclude(is_staff=True).count()
        last_month_users_count = User.objects.exclude(is_staff=True).filter(created_at__lte=last_month_end).count()
        user_growth = ((total_users - last_month_users_count) / last_month_users_count * 100) if last_month_users_count > 0 else 100

        total_active_courses = Course.objects.filter(status="accepted").count()
        last_month_active = Course.objects.filter(status="accepted", created_at__lte=last_month_end).count()
        course_growth = ((total_active_courses - last_month_active) / last_month_active * 100) if last_month_active > 0 else 100

        mtd_revenue = float(Payment.objects.filter(status="success").aggregate(total=Sum("amount"))["total"] or 0)
        last_month_revenue = float(Payment.objects.filter(status="success", paid_at__date__range=[last_month_start, last_month_end]).aggregate(total=Sum("amount"))["total"] or 0)
        revenue_growth = ((mtd_revenue - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 100

        # 📈 2A. Revenue Chart Data (Daily Data for "This Month")
        revenue_labels = []
        revenue_chart = []
        
        # Start from the 1st of the current month up to today
        for day in range(1, today.day + 1):
            target_date = today.replace(day=day)
            revenue_labels.append(target_date.strftime("%b %d"))
            
            # Daily Revenue
            rev_day = Payment.objects.filter(status="success", paid_at__date=target_date).aggregate(total=Sum("amount"))["total"] or 0
            revenue_chart.append(float(rev_day))
            
        # 📊 2B. Course Overview Chart Data (Weekly: Sun to Sat)
        import math
        course_labels = []
        course_chart_views = []
        course_chart_comments = [] 

        # Calculate the Sunday of the current week
        days_since_sunday = (today.weekday() + 1) % 7
        start_of_week = today - timedelta(days=days_since_sunday)
        chart_data = {
            "revenue_chart": {
                "labels": revenue_labels,
                "series": revenue_chart
            },
           
        }

        # 🏆 3. Top Performing Courses
        top_courses_query = Course.objects.filter(status="accepted").annotate(
            enr_count=Count('enrollments')
        ).order_by('-enr_count')[:5]

        top_courses = []
        for c in top_courses_query:
            rev = Payment.objects.filter(status="success", order__items__course=c).aggregate(total=Sum("amount"))["total"] or 0
            top_courses.append({
                "title": c.title,
                "enrollments": getattr(c, 'enr_count', 0),
                "revenue": f"{float(rev):,.0f}"
            })

        # 🌟 4. Top Instructors
        top_instructors_query = User.objects.filter(role="instructor").annotate(
            student_count=Count('courses__enrollments')
        ).order_by('-student_count')[:4]

        top_instructors = []
        for u in top_instructors_query:
            # Calculate average rating across all instructor's courses safely
            courses = u.courses.all()
            total_rating = sum(float(c.rating()) for c in courses if hasattr(c, 'reviews') and c.reviews.exists())
            valid_courses = sum(1 for c in courses if hasattr(c, 'reviews') and c.reviews.exists())
            avg_rating = round(total_rating / valid_courses, 1) if valid_courses > 0 else 4.8
            
            top_instructors.append({
                "name": u.name,
                "avatar": request.build_absolute_uri(u.avatar.url) if u.avatar else None,
                "students": getattr(u, 'student_count', 0),
                "rating": avg_rating
            })

        return APIResponse.success(
            message="Admin analytics data retrieved successfully.",
            data={
                "top_metrics": {
                    "total_users": {
                        "value": f"{total_users:,}",
                        "trend": f"{user_growth:+.1f}% from last period"
                    },
                    "active_courses": {
                        "value": f"{total_active_courses:,}",
                        "trend": f"{course_growth:+.1f}% from last period"
                    },
                    "total_revenue": {
                        "value": f"{mtd_revenue:,.2f}",
                        "trend": f"{revenue_growth:+.1f}% from last period"
                    }
                },
                "charts": chart_data,
                "top_courses": top_courses,
                "top_instructors": top_instructors
            },
            status_code=status.HTTP_200_OK
        )
        
        