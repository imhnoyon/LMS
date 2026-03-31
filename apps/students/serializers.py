from rest_framework import serializers
from apps.users.models import User


class LearnerRegisterSerializer(serializers.ModelSerializer):
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
        user = User.objects.create_user(
            name=validated_data["name"],
            email=validated_data["email"],
            password=validated_data["password"],
            accepted_terms=validated_data["accepted_terms"],
            role="student"
        )
        return user




# deshboard
from rest_framework import serializers
from apps.enrollments.models import Enrollment
from apps.payments.models import Invoice
from apps.courses.models import Course




# 🔹 Course Short Serializer (for dashboard)
class CourseShortSerializer(serializers.ModelSerializer):
    thumbnail = serializers.ImageField(source="advance_info.thumbnail", read_only=True)
    
    class Meta:
        model = Course
        fields = ["id", "title",'subtitle', "thumbnail", "price"]
         
class InvoiceDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            'name',
            "invoice_id",
            'payment_method',
            "amount",
            "status",
            "invoice_date",
            "created_at",
        ]
        
        
class StudentDashboardSerializer(serializers.Serializer):
    enrolled_courses_count = serializers.IntegerField()
    active_courses_count = serializers.IntegerField()
    completed_courses_count = serializers.IntegerField()

    recently_enrolled = CourseShortSerializer(many=True)
    recent_invoices = InvoiceDashboardSerializer(many=True)