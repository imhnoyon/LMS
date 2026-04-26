from django.db import models
from decimal import Decimal
from rest_framework.views import APIView, settings
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from django.db.models import Q
from apps.courses.models import Course
from apps.instructors.serializers import WithdrawalRequestSerializer
from apps.orders.models import Order, OrderItem
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Affiliate, AffiliateCourseLink, AffiliateCommission
from .serializers import AffiliateCourseListSerializer, AffiliateDetailsSerializer, AffiliateListSerializer, AffiliateCommissionHistorySerializer, AffiliatePercentageUpdateSerializer, AffiliateProfileSerializers
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

        #  Trend Calculation (This Month vs Last Month)
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
        
        referral_codes = AffiliateCourseLink.objects.filter(affiliate=affiliate).values_list('code', flat=True)

        total_sales_items = OrderItem.objects.filter(
            order__affiliate_commissions__affiliate=affiliate,
            course=models.F('order__affiliate_commissions__product'),
            order=models.F('order__affiliate_commissions__order')
        ).distinct()
        
        total_sales_amount = total_sales_items.aggregate(models.Sum('paid_price'))['paid_price__sum'] or Decimal("0.00")

        # Sales trends based on items
        sales_now_amount = total_sales_items.filter(
            created_at__gte=this_month_start
        ).aggregate(models.Sum('paid_price'))['paid_price__sum'] or Decimal("0.00")
        
        sales_past_amount = total_sales_items.filter(
            created_at__range=(last_month_start, last_month_end)
        ).aggregate(models.Sum('paid_price'))['paid_price__sum'] or Decimal("0.00")
        
        # Earned trends (from commission records)
        earned_now = AffiliateCommission.objects.filter(
            affiliate=affiliate, status__in=["approved", "paid"],
            created_at__gte=this_month_start
        ).aggregate(Sum('commission_rate'))['commission_rate__sum'] or Decimal("0.00")
        
        earned_past = AffiliateCommission.objects.filter(
            affiliate=affiliate, status__in=["approved", "paid"],
            created_at__range=(last_month_start, last_month_end)
        ).aggregate(Sum('commission_rate'))['commission_rate__sum'] or Decimal("0.00")

        # Pending trends
        pending_now = Withdrawal.objects.filter(user=request.user, status="pending", requested_at__gte=this_month_start).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        pending_past = Withdrawal.objects.filter(user=request.user, status="pending", requested_at__range=(last_month_start, last_month_end)).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        

        # Stats
        # Calculate totals directly from referral click logs for maximum accuracy
        total_clicks = AffiliateReferralClick.objects.filter(affiliate=affiliate).count()
        total_unique_clicks = AffiliateReferralClick.objects.filter(affiliate=affiliate).values('session_key').distinct().count()
        
        if total_unique_clicks == 0 and total_clicks > 0:
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
        
        
        
class AffiliateOverview(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        from django.db.models import Sum, Count
        from apps.affiliates.models import Affiliate, AffiliateCommission
        from django.utils import timezone
        
        # 1. Top Metrics calculation
        total_affiliates = Affiliate.objects.count()
        active_affiliates = Affiliate.objects.filter(status="active").count()
        
        total_commission_generated = float(Affiliate.objects.aggregate(total=Sum("total_earned"))["total"] or 0)
        total_commission_paid = float(Affiliate.objects.aggregate(total=Sum("total_paid"))["total"] or 0)
        pending_payouts = total_commission_generated - total_commission_paid
        
        # Calculate Total Sales derived from affiliate referrals
        total_sales = float(AffiliateCommission.objects.exclude(order__isnull=True).values('order').distinct().aggregate(total=Sum('order__total_amount'))["total"] or 0)

        # 2. Earnings Over Time (Last 6 Months Chart)
        today = timezone.now().date()
        chart_labels = []
        chart_sales = []
        chart_commission_paid = []
        
        for i in range(5, -1, -1):
            target_month = today.month - i
            target_year = today.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            chart_labels.append(timezone.datetime(target_year, target_month, 1).strftime("%b"))
            
            # Fetch Monthly Sales resulting from affiliate recommendations
            monthly_sales = float(AffiliateCommission.objects.filter(
                created_at__year=target_year, created_at__month=target_month, order__isnull=False
            ).values('order').distinct().aggregate(total=Sum('order__total_amount'))["total"] or 0)
            chart_sales.append(monthly_sales)
            
            # Fetch Monthly Commissions generated/paid (we'll query total earned during that month)
            monthly_comm = float(AffiliateCommission.objects.filter(
                created_at__year=target_year, created_at__month=target_month
            ).aggregate(total=Sum('commission_rate'))["total"] or 0)
            chart_commission_paid.append(monthly_comm)

        earnings_over_time = {
            "labels": chart_labels,
            "total_sales": chart_sales,
            "commission_paid": chart_commission_paid
        }

        # 3. Top Performing Affiliates
        top_affiliates_query = Affiliate.objects.annotate(
            sales_count=Count('commissions_records')
        ).order_by('-total_earned')[:4]
        
        top_performers = []
        for index, aff in enumerate(top_affiliates_query):
            top_performers.append({
                "rank": index + 1,
                "name": aff.user.name or "Unknown",
                "sales": getattr(aff, 'sales_count', 0),
                "total_earned": float(aff.total_earned)
            })

        # 4. Affiliates Management Table
        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("type")

        affiliates_query = Affiliate.objects.select_related('user').all()

        if status_filter and status_filter.lower() not in ["all", "all status", ""]:
            affiliates_query = affiliates_query.filter(status__iexact=status_filter)

        if type_filter and type_filter.lower() not in ["all", "all types", ""]:
            # 'type_filter' might be partial words like 'external' or 'territorial'
            affiliates_query = affiliates_query.filter(affiliate_type__icontains=type_filter)

        # Apply pagination to the Affiliates Management Queryset
        paginator = self.pagination_class()
        paginated_affiliates = paginator.paginate_queryset(affiliates_query.order_by('-created_at'), request)

        affiliates_list = []
        for aff in paginated_affiliates:
            # Clean up the type string from Affiliate type to match UI layout ('partner', 'external', 'territorial')
            aff_type = aff.get_affiliate_type_display().split()[0].lower() if aff.get_affiliate_type_display() else "partner"
            
            # Safely format the commission rate to a percentage (e.g., 0.20 -> 20%)
            commission_percent = int(aff.commission_rate * 100) if aff.commission_rate <= 1 else int(aff.commission_rate)
            
            affiliates_list.append({
                "name": aff.user.name or "Unknown",
                "email": aff.user.email,
                "type": aff_type,
                "status": aff.status.upper(),
                "code": aff.id,
                "total_earned": float(aff.total_earned),
                "commission_percent": f"{commission_percent}%",
                "created_date": aff.created_at.strftime("%m/%d/%Y")
            })

        # Return the entire dashboard wrapped inside the Paginated response format
        return paginator.get_paginated_response(
            data={
                "top_metrics": {
                    "total_affiliates": total_affiliates,
                    "active_affiliates": active_affiliates,
                    "total_affiliate_sales": f"${total_sales:,.2f}",
                    "total_commission_paid": f"${total_commission_paid:,.2f}",
                    "total_commission_generated": f"${total_commission_generated:,.2f}",
                    "pending_payouts": f"${pending_payouts:,.2f}"
                },
                "earnings_over_time": earnings_over_time,
                "top_performing_affiliates": top_performers,
                "affiliates_management": affiliates_list
            },
            message="Affiliate overview retrieved successfully."
        )
        
        
class AffiliateBlockview(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)
        
         # Toggle logic
        if affiliate.status == "suspended":
            affiliate.status = "active"
            message = "Affiliate activated successfully."
        else:
            affiliate.status = "suspended"
            message = "Affiliate suspended successfully."
        
        affiliate.save(update_fields=["status"])
        
        return APIResponse.success(
            message=message,
            data={},
            status_code=200
        )
        
        
class UpdateAffiliateCommissionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def patch(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)
        serializer = AffiliatePercentageUpdateSerializer(affiliate,data=request.data, partial=True, context={"request": request})
        
        if not serializer.is_valid():
            return APIResponse.error(
                message="Affiliate update failed.",
                errors=serializer.errors,
                status_code=400
            )
        
        serializer.save()
        return APIResponse.success(
            message="Affiliate updated successfully.",
            data=serializer.data,
            status_code=200
        )
        
        
class AffiliateDetailsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)
        serializer = AffiliateDetailsSerializer(affiliate, context={"request": request})
        return APIResponse.success(
            message="Affiliate details retrieved successfully.",
            data=serializer.data,
            status_code=200
        )
        
        
        
        
class AffiliateWithdrawlistview(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        from apps.payments.models import Withdrawal

        withdrawals = Withdrawal.objects.filter(
            user=request.user
        ).order_by("-requested_at")

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(withdrawals, request)

        serializer = WithdrawalRequestSerializer(paginated_queryset, many=True)

        return paginator.get_paginated_response({
            "message": "Affiliate withdrawal history retrieved successfully.",
            "data": serializer.data
        })