from decimal import Decimal
from rest_framework.views import APIView, settings
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from django.db.models import Q
from apps.courses.models import Course
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Affiliate, AffiliateCourseLink, AffiliateCommission
from .serializers import AffiliateCourseListSerializer, AffiliateListSerializer, AffiliateCommissionHistorySerializer, AffiliateProfileSerializers
from utils.paginations import CustomPagination
from utils.api_response import APIResponse
from .serializers import AffiliateStatusUpdateSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import AffiliateReferralClick
from django.db.models import Sum
from apps.payments.models import Withdrawal


class AffiliateListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")

        affiliates = Affiliate.objects.select_related("user").all()

        #search filter
        if search:
            affiliates = affiliates.filter(
                Q(user__name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(id__icontains=search)
            )

        # status filter
        if status_filter:
            affiliates = affiliates.filter(status=status_filter)

        affiliates = affiliates.order_by("-created_at")

        paginator = self.pagination_class()
        paginated_affiliates = paginator.paginate_queryset(affiliates, request, view=self)
        serializer = AffiliateListSerializer(paginated_affiliates, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="Affiliate list retrieved successfully."
        )
        
        
 

class UpdateAffiliateStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)

        serializer = AffiliateStatusUpdateSerializer(
            affiliate,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0] if serializer.errors else "Invalid data."
            return APIResponse.error(
                message=first_error,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return APIResponse.success(
            message="Affiliate status updated successfully.",
            data={
                "id": affiliate.id,
                "name": affiliate.user.name or affiliate.user.email,
                "email": affiliate.user.email,
                "status": affiliate.status,
            },
            status_code=status.HTTP_200_OK
        )
        
        
# Delete Affiliate View
class DeleteAffiliateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)
        affiliate.delete()

        return APIResponse.success(
            message="Affiliate deleted successfully.",
            data={},
            status_code=status.HTTP_200_OK
        )
        
        
        


# Affiliate course list view for affiliate users
class AffiliateCourseListView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination

    def get(self, request):
        if request.user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can access this course list.",
                status_code=403
            )

        search = request.query_params.get("search")
        category = request.query_params.get("category")

        courses = Course.objects.select_related("category", "advance_info").filter(
            status="accepted"
        ).order_by("-created_at")

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search)
            )

        if category:
            courses = courses.filter(category_id=category)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = AffiliateCourseListSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)
        
        
# Generate course referral link for affiliate users
class GenerateAffiliateCourseLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        user = request.user

        if user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can generate referral links.",
                status_code=403
            )

        affiliate = get_object_or_404(Affiliate, user=user)
        course = get_object_or_404(Course, id=course_id, status="accepted")

        link, created = AffiliateCourseLink.objects.get_or_create(
            affiliate=affiliate,
            course=course
        )

        # Dynamically grab the frontend's exact URL (whether localhost or production)
        base_frontend_url = request.headers.get("Origin")
        if not base_frontend_url:
            base_frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8002")
            
        frontend_url = f"{base_frontend_url}/course/{course.id}?ref={link.code}"

        if link.referral_url != frontend_url:
            link.referral_url = frontend_url
            link.save(update_fields=["referral_url"])

        return APIResponse.success(
            message="Affiliate course link generated successfully.",
            data={
                "course_id": course.id,
                "course_title": course.title,
                "referral_code": link.code,
                "referral_url": link.referral_url
            },
            status_code=200
        )
        
        
from rest_framework.permissions import AllowAny

# Silently track a referral click whenever a user visits a link!
class TrackReferralClickView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        referral_code = request.data.get("referral_code")
        if not referral_code:
            return APIResponse.error("Referral code is missing.", status_code=400)
            
        link = AffiliateCourseLink.objects.filter(code=referral_code).first()
        if not link:
            return APIResponse.error("Invalid referral code.", status_code=404)
            
        # Optional tracking details
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session_key = request.session.session_key if hasattr(request, "session") else None
        
        clicked_by = request.user if request.user.is_authenticated else None
        
        already_clicked = AffiliateReferralClick.objects.filter(
        affiliate_link=link,
        session_key=session_key
        ).exists()
        
        # Log click
        AffiliateReferralClick.objects.create(
            affiliate=link.affiliate,
            course=link.course,
            affiliate_link=link,
            code=referral_code,
            session_key=session_key,
            ip_address=ip_address,
            user_agent=user_agent,
            clicked_by=clicked_by
        )
        
        
        
        # Increment click stats
        link.clicks += 1
        if not already_clicked:
            link.unique_clicks += 1

        link.save(update_fields=["clicks", "unique_clicks"])
        
        return APIResponse.success("Click tracked.", status_code=200)


# Affiliate dashboard view for affiliate users
class AffiliateDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can access this dashboard.",
                status_code=403
            )

        affiliate = get_object_or_404(Affiliate, user=request.user)

        # 📅 Trend Calculation (This Month vs Last Month)
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = this_month_start - timedelta(seconds=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Helper function for trends
        def get_trend(current, last):
            if last == 0:
                return "+100%" if current > 0 else "0%"
            diff = ((current - last) / last) * 100
            return f"+{round(diff, 1)}%" if diff > 0 else f"{round(diff, 1)}%"

        # Clicks trends
        clicks_now = AffiliateReferralClick.objects.filter(affiliate=affiliate, clicked_at__gte=this_month_start).count()
        clicks_past = AffiliateReferralClick.objects.filter(affiliate=affiliate, clicked_at__range=(last_month_start, last_month_end)).count()
        
        # 📊 All referral codes for this affiliate
        referral_codes = AffiliateCourseLink.objects.filter(affiliate=affiliate).values_list('code', flat=True)

        # Total sales amount (Revenue generated by referrals)
        from apps.orders.models import OrderItem
        total_sales_amount = OrderItem.objects.filter(
            referral_code__in=referral_codes
        ).aggregate(Sum('paid_price'))['paid_price__sum'] or Decimal("0.00")

        # Sales trends based on items
        sales_now_amount = OrderItem.objects.filter(referral_code__in=referral_codes, created_at__gte=this_month_start).aggregate(Sum('paid_price'))['paid_price__sum'] or Decimal("0.00")
        sales_past_amount = OrderItem.objects.filter(referral_code__in=referral_codes, created_at__range=(last_month_start, last_month_end)).aggregate(Sum('paid_price'))['paid_price__sum'] or Decimal("0.00")
        
        # Earned trends
        earned_now = AffiliateCommission.objects.filter(affiliate=affiliate, created_at__gte=this_month_start).aggregate(Sum('commission_rate'))['commission_rate__sum'] or Decimal("0.00")
        earned_past = AffiliateCommission.objects.filter(affiliate=affiliate, created_at__range=(last_month_start, last_month_end)).aggregate(Sum('commission_rate'))['commission_rate__sum'] or Decimal("0.00")

        # Pending trends
        pending_now = Withdrawal.objects.filter(user=request.user, status="pending", requested_at__gte=this_month_start).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        pending_past = Withdrawal.objects.filter(user=request.user, status="pending", requested_at__range=(last_month_start, last_month_end)).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        # pending_past = AffiliateCommission.objects.filter(affiliate=affiliate, status__in=["pending", "approved"], created_at__range=(last_month_start, last_month_end)).aggregate(Sum('commission_rate'))['commission_rate__sum'] or Decimal("0.00")

        # 📊 Stats
        # Calculate totals directly from referral click logs for maximum accuracy
        total_clicks = AffiliateReferralClick.objects.filter(affiliate=affiliate).count()
        total_unique_clicks = AffiliateReferralClick.objects.filter(affiliate=affiliate).values('session_key').distinct().count()
        
        if total_unique_clicks == 0 and total_clicks > 0:
            # Fallback to unique IP addresses if no session keys exist (for older data)
            total_unique_clicks = AffiliateReferralClick.objects.filter(affiliate=affiliate).values('ip_address').distinct().count()
        
        
        # Total earned amount
        total_earned = affiliate.total_earned
        
        # Pending commissions (Requested but not yet approved/paid)
        pending_commissions = Withdrawal.objects.filter(
            user=request.user,
            status="pending"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        

        # Wallet details
        total_payable = affiliate.total_payable
        total_paid = affiliate.total_paid
        
        # Progress percentage (Paid vs Earned)
        payout_progress = 0
        if total_earned > 0:
            payout_progress = (total_paid / total_earned) * 100

        stats = {
            "total_clicks": total_clicks,
            "total_unique_clicks": total_unique_clicks,
            "total_sales": total_sales_amount,
            "total_earned": total_earned,
            "pending_Withdraw": pending_commissions,
            "wallet": {
                "total_earned": total_earned,
                "total_payable": total_payable,
                "total_paid": total_paid,
                "payout_progress": round(payout_progress, 1)
            },
            # Real trends from dataset
            "trends": {
                "clicks": get_trend(clicks_now, clicks_past),
                "sales": get_trend(sales_now_amount, sales_past_amount),
                "earned": get_trend(earned_now, earned_past),
                "pending": get_trend(pending_now, pending_past)
            }
        }

        # 📜 Sales History
        sales_query = AffiliateCommission.objects.filter(
            affiliate=affiliate
        ).select_related(
            'product', 
            'order', 
            'order__user'
        ).order_by('-created_at')

        # Simple limit for dashboard overview
        sales_history = sales_query[:10]
        serializer = AffiliateCommissionHistorySerializer(sales_history, many=True)

        return APIResponse.success(
            message="Affiliate dashboard data retrieved successfully.",
            data={
                "stats": stats,
                "sales_history": serializer.data
            },
            status_code=200
        )

# Affiliate Wallet View for affiliate users
class AffiliateWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can access this wallet.",
                status_code=403
            )

        affiliate = get_object_or_404(Affiliate, user=request.user)
        from apps.payments.models import Withdrawal

        # 📊 Wallet Stats
        total_earned = affiliate.total_earned
        total_paid = affiliate.total_paid
        
        # Pending Withdrawals (Requested by the user)
        pending_withdrawals = Withdrawal.objects.filter(
            user=request.user,
            status="pending"
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")

        
        total_payable = affiliate.total_payable - pending_withdrawals
        if total_payable < 0: total_payable = Decimal("0.00")
        
        payout_progress = 0
        if total_earned > 0:
            payout_progress = (total_paid / total_earned) * 100

        wallet_data = {
            "total_earned": total_earned,
            "pending_payment": pending_withdrawals,
            "total_paid": total_paid,
            "total_payable": total_payable,
            "payout_progress": round(payout_progress, 1)
        }

        #  Recent Transactions (Commissions)
        commissions = AffiliateCommission.objects.filter(
            affiliate=affiliate
        ).select_related('product', 'order').order_by('-created_at')[:10]
        
        history_serializer = AffiliateCommissionHistorySerializer(commissions, many=True)

        return APIResponse.success(
            message="Affiliate wallet data retrieved successfully.",
            data={
                "wallet": wallet_data,
                "recent_transactions": history_serializer.data
            },
            status_code=200
        )


# Update affiliate profile 
class AffiliateProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        if request.user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can access this profile.",
                status_code=403
            )

        serializer = AffiliateProfileSerializers(
            request.user,
            context={"request": request}
        )

        return APIResponse.success(
            message="Affiliate profile fetched successfully.",
            data=serializer.data,
            status_code=200
        )


    def patch(self, request):
        if request.user.role != "affiliate":
            return APIResponse.error(
                message="Only affiliate users can update their profile.",
                status_code=403
            )

        serializer = AffiliateProfileSerializers(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if not serializer.is_valid():
            return APIResponse.error(
                message="Profile update failed.",
                errors=serializer.errors,
                status_code=400
            )

        serializer.save()

        return APIResponse.success(
            message="Affiliate profile updated successfully.",
            data=serializer.data,
            status_code=200
        )