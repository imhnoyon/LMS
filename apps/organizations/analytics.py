"""
Organization Analytics & Reporting Module
Handles all analytics calculations, aggregations, and data for organization dashboards
"""
from django.db.models import Sum, Count, Avg, Q, F, DecimalField, FloatField, Case, When, Value, Subquery, OuterRef
from django.db.models.functions import TruncDate, TruncMonth, Coalesce
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date
from apps.payments.models import Commission
from apps.orders.models import Order, OrderItem
from apps.enrollments.models import Enrollment
from apps.courses.models import Course
from apps.courses.models import Review
from django.db.models import Case, When, Value


class OrganizationAnalytics:
    """
    Centralized analytics calculations for organizations
    Optimized with select_related, prefetch_related, and aggregations
    """

    def __init__(self, organization):
        self.organization = organization
        self.now = timezone.now()
        self.today = self.now.date()

    # ═══════════════════════════════════════════════════════════════════════
    # REVENUE ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════

    def get_total_revenue(self, start_date=None, end_date=None):
        """Calculate total revenue based on course discount_price
        Uses OrderItem with course.discount_price (or course.price if no discount)
        """
        query = OrderItem.objects.filter(
            course__organization=self.organization,
            order__status='paid'
        ).annotate(
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        )
        
        if start_date and end_date:
            query = query.filter(order__created_at__date__range=[start_date, end_date])
        
        result = query.aggregate(total=Coalesce(Sum('revenue', output_field=DecimalField()), Decimal('0.00')))
        return result['total']

    def get_today_revenue(self):
        """Calculate today's revenue"""
        return self.get_total_revenue(self.today, self.today)

    def get_monthly_revenue(self, year=None, month=None):
        """Get monthly revenue for a specific month based on discount_price"""
        if not year:
            year = self.today.year
        if not month:
            month = self.today.month

        result = OrderItem.objects.filter(
            course__organization=self.organization,
            order__status='paid',
            order__created_at__year=year,
            order__created_at__month=month
        ).annotate(
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        ).aggregate(total=Coalesce(Sum('revenue', output_field=DecimalField()), Decimal('0.00')))
        
        return result['total']

    def get_revenue_by_month(self, year=None, months_count=12):
        """Get revenue breakdown by month based on discount_price"""
        if not year:
            year = self.today.year

        revenue_data = OrderItem.objects.filter(
            course__organization=self.organization,
            order__status='paid',
            order__created_at__year=year
        ).annotate(
            month=TruncMonth('order__created_at'),
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        ).values('month').annotate(
            total=Coalesce(Sum('revenue', output_field=DecimalField()), Decimal('0.00'))
        ).order_by('month')

        revenue_map = {item['month'].month: item['total'] for item in revenue_data}
        
        result = []
        for month_num in range(1, months_count + 1):
            import calendar
            month_name = calendar.month_abbr[month_num]
            result.append({
                'month': month_num,
                'label': month_name,
                'amount': revenue_map.get(month_num, Decimal('0.00'))
            })
        return result

    def get_revenue_by_specific_months(self, year=None, months=None):
        """Get revenue breakdown for specific months based on discount_price
        Args:
            year: Year to filter by (default: current year)
            months: List of month numbers (1-12) to include
        """
        if not year:
            year = self.today.year
        if not months:
            months = list(range(1, 13))

        revenue_data = OrderItem.objects.filter(
            course__organization=self.organization,
            order__status='paid',
            order__created_at__year=year,
            order__created_at__month__in=months
        ).annotate(
            month=TruncMonth('order__created_at'),
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        ).values('month').annotate(
            total=Coalesce(Sum('revenue', output_field=DecimalField()), Decimal('0.00'))
        ).order_by('month')

        revenue_map = {item['month'].month: item['total'] for item in revenue_data}
        
        import calendar
        result = []
        for month_num in sorted(months):
            if 1 <= month_num <= 12:
                month_name = calendar.month_abbr[month_num]
                result.append({
                    'month': month_num,
                    'label': month_name,
                    'amount': revenue_map.get(month_num, Decimal('0.00'))
                })
        return result

    def get_revenue_by_date_range(self, start_date, end_date):
        """Get daily revenue breakdown for date range based on discount_price"""
        data = OrderItem.objects.filter(
            course__organization=self.organization,
            order__status='paid',
            order__created_at__date__range=[start_date, end_date]
        ).annotate(
            day=TruncDate('order__created_at'),
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        ).values('day').annotate(
            total=Coalesce(Sum('revenue', output_field=DecimalField()), Decimal('0.00'))
        ).order_by('day')

        return [
            {'date': item['day'].isoformat(), 'amount': item['total']}
            for item in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # COURSE & SALES ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════

    def get_total_courses(self):
        """Get total courses count"""
        return Course.objects.filter(organization=self.organization).count()

    def get_active_courses(self):
        """Get active courses count"""
        return Course.objects.filter(
            organization=self.organization,
            status__in=['accepted', 'featured', 'published']
        ).count()

    def get_total_enrollments(self):
        """Get total enrollments across all organization courses"""
        return Enrollment.objects.filter(
            course__organization=self.organization,
            is_active=True
        ).values('user').distinct().count()

    def get_total_enrollments_all_time(self):
        """Get all-time total enrollments"""
        return Enrollment.objects.filter(
            course__organization=self.organization
        ).count()

    def get_course_sales(self, start_date=None, end_date=None):
        """Get total course sales count based on OrderItem (paid orders only)"""
        query = OrderItem.objects.filter(
            course__organization=self.organization,
            order__status='paid'
        )
        
        if start_date and end_date:
            query = query.filter(order__created_at__date__range=[start_date, end_date])
        
        return query.count()

    def get_average_course_price(self):
        """Calculate average course price using discount_price"""
        result = Course.objects.filter(
            organization=self.organization
        ).annotate(
            effective_price=Case(
                When(discount_price__isnull=False, then=F('discount_price')),
                default=F('price'),
                output_field=DecimalField()
            )
        ).aggregate(avg_price=Coalesce(Avg('effective_price', output_field=DecimalField()), Decimal('0.00')))
        return result['avg_price']

    def get_course_enrollment_stats(self):
        """Get enrollment statistics per course using discount_price for revenue"""
        from django.db.models import Subquery, OuterRef
        
        # Subquery to calculate revenue per course using discount_price
        revenue_subquery = OrderItem.objects.filter(
            course=OuterRef('id'),
            order__status='paid'
        ).annotate(
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        ).values('course').annotate(
            total=Sum('revenue', output_field=DecimalField())
        ).values('total')
        
        courses = Course.objects.filter(
            organization=self.organization
        ).annotate(
            total_enrollments=Count('enrollments', filter=Q(enrollments__is_active=True)),
            total_revenue=Coalesce(
                Subquery(revenue_subquery),
                Decimal('0.00')
            )
        ).values(
            'id', 'title', 'price', 'discount_price', 'status', 'total_enrollments', 'total_revenue'
        ).order_by('-total_enrollments')
        
        return list(courses)

    def get_top_courses(self, limit=5):
        """Get top performing courses by enrollments"""
        return self.get_course_enrollment_stats()[:limit]

    # ═══════════════════════════════════════════════════════════════════════
    # RATINGS & REVIEWS
    # ═══════════════════════════════════════════════════════════════════════

    def get_average_rating(self):
        """Get average course rating"""
        result = Review.objects.filter(
            course__organization=self.organization
        ).aggregate(avg_rating=Coalesce(Avg('rating', output_field=FloatField()), 0.0))
        return float(result['avg_rating'] or 0.0)

    def get_total_reviews(self):
        """Get total reviews count"""
        return Review.objects.filter(
            course__organization=self.organization
        ).count()

    def get_rating_breakdown(self):
        """Get rating distribution breakdown"""
        total_reviews = self.get_total_reviews()
        if total_reviews == 0:
            return [{'stars': i, 'count': 0, 'percentage': 0.0} for i in range(5, 0, -1)]

        breakdown = []
        for stars in [5, 4, 3, 2, 1]:
            count = Review.objects.filter(
                course__organization=self.organization,
                rating=stars
            ).count()
            percentage = round((count / total_reviews) * 100, 2) if total_reviews > 0 else 0.0
            breakdown.append({
                'stars': stars,
                'count': count,
                'percentage': percentage
            })
        return breakdown

    # ═══════════════════════════════════════════════════════════════════════
    # ORDERS & TRANSACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def get_recent_orders(self, limit=10, start_date=None, end_date=None):
        """Get recent paid orders"""
        query = Order.objects.filter(
            items__course__organization=self.organization,
            status='paid'
        ).distinct().select_related('user').prefetch_related('items__course')

        if start_date and end_date:
            query = query.filter(created_at__date__range=[start_date, end_date])

        return query.order_by('-created_at')[:limit]

    def get_recent_commissions(self, limit=10, start_date=None, end_date=None):
        """Get recent commission records"""
        query = Commission.objects.filter(
            course__organization=self.organization
        ).select_related('user', 'course')

        if start_date and end_date:
            query = query.filter(created_at__date__range=[start_date, end_date])

        return query.order_by('-created_at')[:limit]

    def get_recently_created_courses(self, limit=5):
        """Get recently created courses"""
        return Course.objects.filter(
            organization=self.organization
        ).annotate(
            enrolled_count=Count('enrollments', filter=Q(enrollments__is_active=True))
        ).select_related('category').order_by('-created_at')[:limit]

    # ═══════════════════════════════════════════════════════════════════════
    # INSTRUCTOR & TEAM ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════

    def get_instructor_earnings(self):
        """Get earnings per instructor based on discount_price"""
        from apps.organizations.models import Membership
        
        # Subquery to calculate total earnings per instructor using discount_price
        earnings_subquery = OrderItem.objects.filter(
            course__instructor__user_id=OuterRef('user__id'),
            order__status='paid'
        ).annotate(
            revenue=Case(
                When(course__discount_price__isnull=False, then=F('course__discount_price')),
                default=F('course__price'),
                output_field=DecimalField()
            )
        ).values('course__instructor__user_id').annotate(
            total=Sum('revenue', output_field=DecimalField())
        ).values('total')
        
        instructors = Membership.objects.filter(
            organization=self.organization,
            role=Membership.Role.INSTRUCTOR
        ).select_related('user').annotate(
            total_earnings=Coalesce(
                Subquery(earnings_subquery),
                Decimal('0.00')
            ),
            courses_count=Count('user__courses', filter=Q(user__courses__organization=self.organization)),
            enrollments_count=Count(
                'user__courses__enrollments',
                filter=Q(user__courses__organization=self.organization, user__courses__enrollments__is_active=True)
            )
        ).values(
            'id', 'user__id', 'user__name', 'user__email', 'total_earnings', 'courses_count', 'enrollments_count'
        ).order_by('-total_earnings')

        return list(instructors)

    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARY DASHBOARD STATS
    # ═══════════════════════════════════════════════════════════════════════

    def get_dashboard_summary(self, start_date=None, end_date=None):
        """Get complete dashboard summary"""
        return {
            'total_revenue': self.get_total_revenue(start_date, end_date),
            'today_revenue': self.get_today_revenue(),
            'total_courses': self.get_total_courses(),
            'active_courses': self.get_active_courses(),
            'total_enrollments': self.get_total_enrollments(),
            'total_enrollments_all_time': self.get_total_enrollments_all_time(),
            'average_rating': self.get_average_rating(),
            'total_reviews': self.get_total_reviews(),
            'average_course_price': float(self.get_average_course_price()),
            'course_sales': self.get_course_sales(start_date, end_date),
        }
