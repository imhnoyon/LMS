"""
Organization Analytics & Reporting Views
Comprehensive API endpoints for organization dashboards and analytics
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from datetime import date, timedelta
from decimal import Decimal

from apps.organizations.models import Organization, Membership
from apps.organizations.analytics import OrganizationAnalytics
from apps.organizations.analytics_serializers import (
    DashboardSummarySerializer,
    MonthlyRevenueChartSerializer,
    DailyRevenueChartSerializer,
    TopCourseSerializer,
    RecentOrderSerializer,
    CommissionSerializer,
    RecentlyCreatedCourseSerializer,
    InstructorAnalyticsSerializer,
    RatingBreakdownSerializer,
    CourseAnalyticsSerializer,
    OrganizationReportSerializer,
    AnalyticsFilterSerializer,
)
from apps.payments.models import Commission
from apps.orders.models import Order
from apps.courses.models import Course, Review
from apps.enrollments.models import Enrollment
from utils.api_response import APIResponse
from utils.paginations import CustomPagination


# ═══════════════════════════════════════════════════════════════════════════
# BASE MIXIN FOR ORGANIZATION ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════════

class OrganizationAnalyticsMixin:
    """Mixin for organization-scoped analytics access control"""
    permission_classes = [IsAuthenticated]

    def get_user_organization(self, user):
        """Get user's organization with admin/manager permission check"""
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER]
        ).select_related("organization").first()

    def get_analytics_or_error(self, request):
        """Get organization analytics or return error"""
        org_membership = self.get_user_organization(request.user)
        if not org_membership:
            return None, APIResponse.error(
                message="You do not have permission to access analytics for this organization.",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return OrganizationAnalytics(org_membership.organization), None


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD STATISTICS VIEW
# ═══════════════════════════════════════════════════════════════════════════

class DashboardStatisticsView(OrganizationAnalyticsMixin, APIView):
    """
    Comprehensive dashboard statistics with optional date filtering
    GET /api/v1/organizations/dashboard-statistics/
    Query params: start_date, end_date (YYYY-MM-DD format)
    """

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        # Parse date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date and end_date:
            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        summary = analytics.get_dashboard_summary(start_date, end_date)
        serializer = DashboardSummarySerializer(summary)

        return APIResponse.success(
            message="Dashboard statistics retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════
# REVENUE TRENDS VIEW
# ═══════════════════════════════════════════════════════════════════════════

class RevenueTrendsView(OrganizationAnalyticsMixin, APIView):
    """
    Revenue trends and forecasting
    GET /api/v1/organizations/revenue-trends/
    Query params:
        - year (optional): Year to filter by (default: current year)
        - months_count (optional): Number of months to return (default: 12)
        - months (optional): Comma-separated month numbers (1-12) e.g., "1,3,5"
    
    Examples:
        /revenue-trends/ - All months of current year
        /revenue-trends/?year=2025 - All months of 2025
        /revenue-trends/?months=1,3,5 - Jan, Mar, May of current year
        /revenue-trends/?year=2025&months=1,3,5 - Jan, Mar, May of 2025
        /revenue-trends/?months_count=6 - First 6 months of current year
    """

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        year = request.query_params.get('year')
        months_param = request.query_params.get('months')
        months_count = request.query_params.get('months_count')

        try:
            if year:
                year = int(year)
            
            # If specific months are provided, use them
            if months_param:
                try:
                    months = [int(m.strip()) for m in months_param.split(',')]
                    # Validate months are between 1-12
                    if not all(1 <= m <= 12 for m in months):
                        return APIResponse.error(
                            message="Month numbers must be between 1 and 12.",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    revenue_data = analytics.get_revenue_by_specific_months(year, months)
                except ValueError:
                    return APIResponse.error(
                        message="Invalid months format. Use comma-separated numbers (1-12).",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Use months_count for range-based filtering
                if months_count:
                    months_count = int(months_count)
                    if months_count < 1 or months_count > 12:
                        return APIResponse.error(
                            message="months_count must be between 1 and 12.",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    months_count = 12
                revenue_data = analytics.get_revenue_by_month(year, months_count)
        except (ValueError, TypeError):
            return APIResponse.error(
                message="Invalid parameters. year must be integer, months must be comma-separated numbers.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = MonthlyRevenueChartSerializer(revenue_data, many=True)

        return APIResponse.success(
            message="Revenue trends retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════
# DAILY REVENUE CHART VIEW
# ═══════════════════════════════════════════════════════════════════════════

class DailyRevenueChartView(OrganizationAnalyticsMixin, APIView):
    """
    Daily revenue breakdown for date range
    GET /api/v1/organizations/daily-revenue/
    Query params: start_date (required), end_date (required) - Format: YYYY-MM-DD
    """

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return APIResponse.error(
                message="start_date and end_date are required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return APIResponse.error(
                message="Invalid date format. Use YYYY-MM-DD",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if start_date > end_date:
            return APIResponse.error(
                message="start_date must be before end_date.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        revenue_data = analytics.get_revenue_by_date_range(start_date, end_date)
        serializer = DailyRevenueChartSerializer(revenue_data, many=True)

        return APIResponse.success(
            message="Daily revenue chart retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════
# COURSE ANALYTICS VIEW
# ═══════════════════════════════════════════════════════════════════════════

class CourseAnalyticsView(OrganizationAnalyticsMixin, APIView):
    """
    Course-level analytics with enrollment and revenue stats
    GET /api/v1/organizations/course-analytics/
    Query params: limit (optional), offset (optional)
    """
    pagination_class = CustomPagination

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        course_stats = analytics.get_course_enrollment_stats()
        
        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(course_stats, request, view=self)
        serializer = CourseAnalyticsSerializer(paginated_data, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="Course analytics retrieved successfully."
        )


# ═══════════════════════════════════════════════════════════════════════════
# TOP COURSES VIEW
# ═══════════════════════════════════════════════════════════════════════════

class TopCoursesView(OrganizationAnalyticsMixin, APIView):
    """
    Top performing courses by enrollments and revenue
    GET /api/v1/organizations/top-courses/
    Query params: limit (default=5, max=20)
    """

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        limit = request.query_params.get('limit', 5)
        try:
            limit = min(int(limit), 20)
        except (ValueError, TypeError):
            limit = 5

        top_courses = analytics.get_top_courses(limit)
        serializer = TopCourseSerializer(top_courses, many=True)

        return APIResponse.success(
            message="Top courses retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════
# RECENT ACTIVITY VIEW
# ═══════════════════════════════════════════════════════════════════════════

class RecentActivityView(OrganizationAnalyticsMixin, APIView):
    """
    Recent orders, commissions, and course additions
    GET /api/v1/organizations/recent-activity/
    Query params: limit (default=10)
    """
    pagination_class = CustomPagination

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 10

        # Get recent activity data
        recent_orders = analytics.get_recent_orders(limit)
        recent_commissions = analytics.get_recent_commissions(limit)
        recent_courses = analytics.get_recently_created_courses(5)

        data = {
            'recent_orders': {
                'count': recent_orders.count(),
                'data': self._format_orders(recent_orders)
            },
            'recent_commissions': {
                'count': recent_commissions.count(),
                'data': CommissionSerializer(recent_commissions, many=True).data
            },
            'recent_courses': {
                'count': recent_courses.count(),
                'data': RecentlyCreatedCourseSerializer(recent_courses, many=True).data
            }
        }

        return APIResponse.success(
            message="Recent activity retrieved successfully.",
            data=data,
            status_code=status.HTTP_200_OK
        )

    def _format_orders(self, orders):
        """Format order data for response"""
        result = []
        for order in orders:
            result.append({
                'order_id': order.order_id,
                'user_name': order.user.name,
                'user_email': order.user.email,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at
            })
        return result


# ═══════════════════════════════════════════════════════════════════════════
# INSTRUCTOR ANALYTICS VIEW
# ═══════════════════════════════════════════════════════════════════════════

class InstructorAnalyticsView(OrganizationAnalyticsMixin, APIView):
    """
    Instructor performance and earnings analytics
    GET /api/v1/organizations/instructor-analytics/
    Query params: limit (optional)
    """
    pagination_class = CustomPagination

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        instructor_data = analytics.get_instructor_earnings()
        
        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(instructor_data, request, view=self)
        serializer = InstructorAnalyticsSerializer(paginated_data, many=True)

        return paginator.get_paginated_response(
            serializer.data,
            message="Instructor analytics retrieved successfully."
        )


# ═══════════════════════════════════════════════════════════════════════════
# RATINGS BREAKDOWN VIEW
# ═══════════════════════════════════════════════════════════════════════════

class RatingsBreakdownView(OrganizationAnalyticsMixin, APIView):
    """
    Course ratings distribution breakdown
    GET /api/v1/organizations/ratings-breakdown/
    """

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        rating_data = {
            'average_rating': analytics.get_average_rating(),
            'total_reviews': analytics.get_total_reviews(),
            'breakdown': analytics.get_rating_breakdown()
        }

        serializer = RatingBreakdownSerializer(rating_data['breakdown'], many=True)

        return APIResponse.success(
            message="Ratings breakdown retrieved successfully.",
            data={
                'average_rating': rating_data['average_rating'],
                'total_reviews': rating_data['total_reviews'],
                'breakdown': serializer.data
            },
            status_code=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE REPORT VIEW
# ═══════════════════════════════════════════════════════════════════════════

class ComprehensiveReportView(OrganizationAnalyticsMixin, APIView):
    """
    Complete organization analytics report with all data
    GET /api/v1/organizations/comprehensive-report/
    Query params: start_date, end_date, include_detailed (true/false, default=true)
    """

    def get(self, request):
        analytics, error = self.get_analytics_or_error(request)
        if error:
            return error

        # Parse parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        include_detailed = request.query_params.get('include_detailed', 'true').lower() == 'true'
        today = timezone.now().date()

        if not start_date or not end_date:
            start_date = today - timedelta(days=30)
            end_date = today
        else:
            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # Compile comprehensive report
        report_data = {
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'start_date': start_date,
            'end_date': end_date,
            'summary': analytics.get_dashboard_summary(start_date, end_date),
            'revenue_trends': analytics.get_revenue_by_month(),
            'daily_revenue': analytics.get_revenue_by_date_range(start_date, end_date) if include_detailed else [],
            'top_courses': analytics.get_top_courses(10),
            'course_analytics': analytics.get_course_enrollment_stats() if include_detailed else [],
            'average_rating': analytics.get_average_rating(),
            'total_reviews': analytics.get_total_reviews(),
            'rating_breakdown': analytics.get_rating_breakdown(),
            'recent_orders': self._format_orders(analytics.get_recent_orders(10, start_date, end_date)),
            'recent_commissions': analytics.get_recent_commissions(10, start_date, end_date),
            'recently_created_courses': analytics.get_recently_created_courses(5),
            'instructor_analytics': analytics.get_instructor_earnings()
        }

        serializer = OrganizationReportSerializer(report_data)

        return APIResponse.success(
            message="Comprehensive report generated successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def _format_orders(self, orders):
        """Format order data for response"""
        result = []
        for order in orders:
            result.append({
                'order_id': order.order_id,
                'user_name': order.user.name,
                'user_email': order.user.email,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at
            })
        return result
