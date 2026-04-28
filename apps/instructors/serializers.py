from rest_framework import serializers
from apps.instructors.models import Instructor
from apps.organizations.models import Invitation, Membership
from apps.payments.models import Withdrawal
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
    def validate_name(self, value):
        if User.objects.filter(name=value).exists():
            raise serializers.ValidationError("Name already exists.")
        return value
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
from apps.courses.models import Course      
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
    class Meta:
        model = Withdrawal
        fields = ['id','withdraw_id', 'user_name', 'bank_name', 'bank_last4', 'amount', 'status', 'requested_at']
        
        
        
        
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