"""
Organization Analytics Serializers
Handles serialization of all analytics data, reports, and dashboard metrics
"""
from rest_framework import serializers
from apps.orders.models import Order
from apps.payments.models import Commission
from apps.courses.models import Course
from apps.enrollments.models import Enrollment
from apps.users.models import User
from django.utils.timesince import timesince


# ═══════════════════════════════════════════════════════════════════════════
# CHART & ANALYTICS DATA SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class ChartDataPointSerializer(serializers.Serializer):
    """Generic chart data point"""
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class MonthlyRevenueChartSerializer(serializers.Serializer):
    """Monthly revenue chart data"""
    month = serializers.IntegerField()
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class DailyRevenueChartSerializer(serializers.Serializer):
    """Daily revenue chart data"""
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class RatingBreakdownSerializer(serializers.Serializer):
    """Rating distribution breakdown"""
    stars = serializers.IntegerField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


# ═══════════════════════════════════════════════════════════════════════════
# COURSE ANALYTICS SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class CourseAnalyticsSerializer(serializers.Serializer):
    """Course analytics including enrollments and revenue"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=8, decimal_places=2)
    status = serializers.CharField()
    total_enrollments = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class TopCourseSerializer(serializers.Serializer):
    """Top performing courses"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=8, decimal_places=2)
    enrollments = serializers.IntegerField(source='total_enrollments')
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2, source='total_revenue')


class RecentlyCreatedCourseSerializer(serializers.ModelSerializer):
    """Recently created courses with stats"""
    enrolled_count = serializers.IntegerField()
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'price', 'status', 'enrolled_count', 'category_name', 'created_at']


# ═══════════════════════════════════════════════════════════════════════════
# ORDER & TRANSACTION SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class RecentOrderSerializer(serializers.Serializer):
    """Recent order details"""
    order_id = serializers.CharField()
    user_name = serializers.CharField()
    user_email = serializers.EmailField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    courses_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class CommissionSerializer(serializers.ModelSerializer):
    """Commission transaction details"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Commission
        fields = ['id', 'user_name', 'course_title', 'order_amount', 'commission_amount', 'created_at']


class RecentTransactionSerializer(serializers.Serializer):
    """Recent transaction for earnings table"""
    transaction_id = serializers.CharField()
    user_name = serializers.CharField()
    course_title = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    date = serializers.DateTimeField()
    type = serializers.CharField()


# ═══════════════════════════════════════════════════════════════════════════
# INSTRUCTOR ANALYTICS SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class InstructorAnalyticsSerializer(serializers.Serializer):
    """Instructor earnings and performance analytics"""
    instructor_id = serializers.IntegerField(source='id')
    user_id = serializers.IntegerField(source='user__id')
    name = serializers.CharField(source='user__name')
    email = serializers.EmailField(source='user__email')
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    courses_count = serializers.IntegerField()
    enrollments_count = serializers.IntegerField()


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD SUMMARY SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class DashboardSummarySerializer(serializers.Serializer):
    """Complete dashboard summary statistics"""
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    today_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_courses = serializers.IntegerField()
    active_courses = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    total_enrollments_all_time = serializers.IntegerField()
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    average_course_price = serializers.FloatField()
    course_sales = serializers.IntegerField()


class OrganizationReportSerializer(serializers.Serializer):
    """Comprehensive organization report"""
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
    # Summary metrics
    summary = DashboardSummarySerializer()
    
    # Revenue data
    revenue_trends = MonthlyRevenueChartSerializer(many=True)
    daily_revenue = DailyRevenueChartSerializer(many=True)
    
    # Courses
    top_courses = TopCourseSerializer(many=True)
    course_analytics = CourseAnalyticsSerializer(many=True)
    
    # Reviews
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    rating_breakdown = RatingBreakdownSerializer(many=True)
    
    # Recent activity
    recent_orders = RecentOrderSerializer(many=True)
    recent_commissions = CommissionSerializer(many=True)
    recently_created_courses = RecentlyCreatedCourseSerializer(many=True)
    
    # Instructors
    instructor_analytics = InstructorAnalyticsSerializer(many=True)


class AnalyticsFilterSerializer(serializers.Serializer):
    """Filtering options for analytics queries"""
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    year = serializers.IntegerField(required=False)
    course_id = serializers.IntegerField(required=False)
    period = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly', 'yearly'],
        required=False
    )


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT/REPORT SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class ReportExportOptionsSerializer(serializers.Serializer):
    """Options for report export"""
    format = serializers.ChoiceField(choices=['json', 'csv', 'pdf', 'excel'])
    include_charts = serializers.BooleanField(default=False)
    include_detailed_data = serializers.BooleanField(default=True)
    date_range = serializers.CharField(required=False)


class DownloadableReportSerializer(serializers.Serializer):
    """Downloadable report metadata"""
    report_id = serializers.CharField()
    title = serializers.CharField()
    format = serializers.CharField()
    file_url = serializers.URLField()
    file_size = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
