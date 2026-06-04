from rest_framework import serializers
from apps.instructors.models import Instructor
from apps.organizations.models import Invitation, Membership
from apps.payments.models import Withdrawal
from apps.enrollments.models import Certificate
from apps.students.models import Student
from apps.users.models import User

class InstructorRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["name", "email", "password", "confirm_password", "accepted_terms"]
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8}
        }
   
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        if not attrs.get("accepted_terms", False):
            raise serializers.ValidationError({
                "accepted_terms": "You must accept the terms and conditions."
            })
             
        return attrs
    
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data.pop("invite_token", None)
        user = User.objects.create_user(
            name=validated_data["name"],
            email=validated_data["email"],
            password=validated_data["password"],
            accepted_terms=validated_data["accepted_terms"],
            role="instructor"
        )
        Instructor.objects.create(user=user)
        return user
    
    
    
    

# Serializer for listing pending instructors

from apps.instructors.models import Instructor
class PendingInstructorListSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Instructor
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "phone",
            "title",
            "biography",
            "is_approved",
            "is_featured",
        ]


class ApproveInstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ["is_approved", "is_featured"]

    def update(self, instance, validated_data):
        instance.is_approved = validated_data.get("is_approved", instance.is_approved)
        instance.is_featured = validated_data.get("is_featured", instance.is_featured)
        instance.save()
        return instance
    
    
    
    
# course course
from apps.courses.models import Course, Review      
class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'subtitle', 'category', 'topic', 'language', 'level', 'price', 'discount_price','rating', 'coupon_code', 'expiry_type', 'status', 'created_at']
        
        
        
        
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'avatar']
        read_only_fields = ['id', 'email']

class InstructorProfileSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer()

    class Meta:
        model = Instructor
        fields = ['id', 'title', 'biography','website', 'twitter', 'linkedin', 'youtube', 'user']
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        return instance
    
    
    
    
 # Dashboard serializers   
class RecentActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    student_name = serializers.CharField()
    course_title = serializers.CharField()
    message = serializers.CharField()
    created_at = serializers.DateTimeField()


class RevenueChartSerializer(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class CourseOverviewChartSerializer(serializers.Serializer):
    label = serializers.CharField()
    enrollments = serializers.IntegerField()
    completions = serializers.IntegerField()


class RatingBreakdownSerializer(serializers.Serializer):
    stars = serializers.IntegerField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class InstructorDashboardSerializer(serializers.Serializer):
    course_created = serializers.IntegerField()
    active_courses = serializers.IntegerField()
    students_enrolled = serializers.IntegerField()
    online_students = serializers.IntegerField()
    online_courses = serializers.IntegerField()
    total_earning = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_rating = serializers.FloatField()
    recent_activity = RecentActivitySerializer(many=True)
    monthly_revenue_chart = RevenueChartSerializer(many=True)
    rating_breakdown = RatingBreakdownSerializer(many=True)
    course_overview_chart = CourseOverviewChartSerializer(many=True)
    
    
    
    
# Earnings serializers
class WithdrawalSerializer(serializers.ModelSerializer):
   class Meta:
        model = Withdrawal
        fields = ['id','withdraw_id', 'user_name', 'bank_name', 'bank_last4', 'amount', 'status', 'requested_at']
    
class RevenueChartSerializer2(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
class InstructorEarningsSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_withdrawals = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    withdrawals = WithdrawalSerializer(many=True, read_only=True)
    monthly_revenue_chart = RevenueChartSerializer2(many=True)



# Withdraw request serializer
class WithdrawalRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_role= serializers.CharField(source="user.role", read_only=True)
    user_image = serializers.SerializerMethodField()
    email= serializers.EmailField(source="user.email", read_only=True)
    class Meta:
        model = Withdrawal
        fields = ['id','withdraw_id', 'user_name', 'user_role','email', 'bank_name', 'bank_last4', 'amount', 'status', 'requested_at','user_image']
        
    def get_user_image(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None
        
        
        
        
class InstructorSignatureSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    signature = serializers.SerializerMethodField()
    
    class Meta:
        model = Instructor
        fields = ['id','name', 'email','signature',]
        read_only_fields = ['id']
    
    def get_signature(self, obj):
        if obj.signature:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.signature.url) if request else obj.signature.url
        return None


class InstructorCertificateSerializer(serializers.ModelSerializer):
    certificated_id = serializers.SerializerMethodField()
    
    
    class Meta:
        model = Course
        fields = ["id",'certificated_id',  "title", "subtitle", "topic", "language", "status", "created_at"]
        
        
        
    def get_certificated_id(self, obj):
        from apps.enrollments.models import Certificate
        # Get first certificate issued for this course
        certificate = Certificate.objects.filter(
            enrollment__course=obj
        ).order_by('-issue_date').first()
        
        if certificate:
            return certificate.certificate_id
        
        return None
    
   
    
class SignatureUploadSerializer(serializers.Serializer):
    signature = serializers.ImageField(required=True)
    
    def validate_signature(self, value):
        """Validate signature file size and type"""
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError("Signature file size must not exceed 5MB.")
        
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only JPEG, PNG, and GIF images are allowed.")
        
        return value


class UserSignatureSerializer(serializers.ModelSerializer):
    signature_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'signature', 'signature_url']
        read_only_fields = ['id', 'name', 'email']
    
    def get_signature_url(self, obj):
        if obj.signature:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.signature.url) if request else obj.signature.url
        return None
 
class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="user.name", read_only=True)
    student_avatar = serializers.SerializerMethodField()
    course_title = serializers.CharField(source="course.title", read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'student_name', 'student_avatar', 'course_title', 'rating', 'comment', 'created_at']
    
    def get_student_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None

class courseDetailShortviewSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'subtitle', 'category', 'topic', 'language', 'level', 'price', 'discount_price','rating',  'status','thumbnail', 'total_students']
        
    def get_thumbnail(self, obj):
        try:
            if obj.advance_info and obj.advance_info.thumbnail:
                request = self.context.get('request')
                return request.build_absolute_uri(obj.advance_info.thumbnail.url) if request else obj.advance_info.thumbnail.url
        except:
            pass
        return None
    
    def get_rating(self, obj):
        return obj.rating() if callable(obj.rating) else obj.rating
    
    def get_total_students(self, obj):
        return obj.enrollments.count()
 
class InstructorProfileDetailSerializer(serializers.ModelSerializer):
    courses = courseDetailShortviewSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    average_rating = serializers.SerializerMethodField()
    total_courses = serializers.IntegerField(source="courses.count", read_only=True)
    total_students = serializers.SerializerMethodField()
    avatar = serializers.CharField(source="user.avatar", read_only=True)
    
    class Meta:
        model = Instructor
        fields = ['id', 'name', 'email', 'total_students','title', 'biography','website', 'twitter', 'linkedin', 'youtube','avatar','average_rating','total_courses','courses','reviews']
        read_only_fields = ['id']
    
    def get_average_rating(self, obj):
        """Calculate average rating from all instructor's courses"""
        courses = obj.courses.all()
        if not courses.exists():
            return 0
        
        total_rating = 0
        count = 0
        for course in courses:
            rating = course.rating()
            if rating > 0:
                total_rating += rating
                count += 1
        
        if count == 0:
            return 0
        
        return round(total_rating / count, 1)
    
    
    def get_total_students(self, obj):
        """Calculate total students across all instructor's courses"""
        courses = obj.courses.all()
        total_students = sum(course.enrollments.count() for course in courses)
        return total_students
    
    def get_reviews(self, obj):
        """Get all reviews from all instructor's courses"""
        courses = obj.courses.all()
        all_reviews = Review.objects.filter(course__in=courses).select_related('user', 'course').order_by('-created_at')
        serializer = ReviewSerializer(all_reviews, many=True, context=self.context)
        return serializer.data
    
    
    
# Serializer for instructor's profile view
class InstructorProfileListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    avatar = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    code = serializers.CharField(source="id", read_only=True)
    total_earned = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Instructor
        fields = [
            'id', 'name', 'email', 'phone', 'avatar', 'title', 'biography','type', 'status', 'code', 'total_earned', 'created_date'
        ]
        read_only_fields = ['id', 'name', 'email', 'phone', 'avatar', 'code', 'total_earned', 'created_date']

    def get_type(self, obj):
        return 'Instructor'
    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None

    def get_status(self, obj):
        user = getattr(obj, 'user', None)
        if user and not user.is_active:
            return 'SUSPENDED'
        if obj.is_approved:
            return 'ACTIVE'
        return 'PENDING'

    def get_total_earned(self, obj):
        from django.db.models import Sum
        from apps.payments.models import Commission

        total = Commission.objects.filter(user=obj.user).aggregate(total=Sum('commission_amount'))['total']
        if total is None:
            return 0
        return total

    def get_created_date(self, obj):
        if obj.created_at:
            return obj.created_at
        return None
    
    
class AdminInstructorProfileListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    avatar = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    code = serializers.CharField(source="id", read_only=True)
    total_earned = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Instructor
        fields = [
            'id', 'name', 'email', 'phone', 'avatar', 'title', 'biography','website','twitter','linkedin','youtube','type', 'status', 'code', 'total_earned', 'created_date'
        ]
        read_only_fields = ['id', 'name', 'email', 'phone', 'avatar', 'code', 'total_earned', 'created_date']

    def get_type(self, obj):
        return 'Instructor'
    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None

    def get_status(self, obj):
        user = getattr(obj, 'user', None)
        if user and not user.is_active:
            return 'SUSPENDED'
        if obj.is_approved:
            return 'ACTIVE'
        return 'PENDING'

    def get_total_earned(self, obj):
        from django.db.models import Sum
        from apps.payments.models import Commission

        total = Commission.objects.filter(user=obj.user).aggregate(total=Sum('commission_amount'))['total']
        if total is None:
            return 0
        return total

    def get_created_date(self, obj):
        if obj.created_at:
            return obj.created_at
        return None