from rest_framework import serializers
from apps.users.models import User
from apps.enrollments.models import Enrollment
from apps.payments.models import Invoice
from apps.courses.models import (
    Course, Section, Lecture, LecturesProgress, 
    Quiz, QuizAttempt, Question, QuestionOption
)
from .helper_funtion import is_lecture_accessible, is_quiz_passed

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




# 🔹 Dashboard Serializers
class CourseShortSerializer(serializers.ModelSerializer):
    thumbnail = serializers.ImageField(source="advance_info.thumbnail", read_only=True)
    class Meta:
        model = Course
        fields = ["id", "title",'subtitle', "thumbnail", "price"]
         
class InvoiceDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "name", "invoice_id", 'payment_method', "amount", "status", "invoice_date", "created_at"]
        
class StudentDashboardSerializer(serializers.Serializer):
    enrolled_courses_count = serializers.IntegerField()
    active_courses_count = serializers.IntegerField()
    completed_courses_count = serializers.IntegerField()
    recently_enrolled = CourseShortSerializer(many=True)
    recent_invoices = InvoiceDashboardSerializer(many=True)

# 🔹 Course Player Serializers
class LecturePlayerSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = ["id", "name", "order", "is_completed", "is_unlocked", "video_file", "description"]

    def get_is_completed(self, obj):
        user = self.context["request"].user
        return LecturesProgress.objects.filter(user=user, lecture=obj, is_completed=True).exists()

    def get_is_unlocked(self, obj):
        user = self.context["request"].user
        return is_lecture_accessible(user, obj)

class QuizMiniSerializer(serializers.ModelSerializer):
    is_passed = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "passing_score", "is_passed", "is_unlocked"]

    def get_is_passed(self, obj):
        user = self.context["request"].user
        return is_quiz_passed(user, obj)

    def get_is_unlocked(self, obj):
        user = self.context["request"].user
        # Quiz is unlocked if all lectures in section are finished
        unfinished_lectures = Lecture.objects.filter(section=obj.section).exclude(
            id__in=LecturesProgress.objects.filter(user=user, is_completed=True).values_list('lecture_id', flat=True)
        ).exists()
        return not unfinished_lectures

class SectionPlayerSerializer(serializers.ModelSerializer):
    lectures = LecturePlayerSerializer(many=True, read_only=True)
    quizzes = QuizMiniSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ["id", "name", "order", "lectures", "quizzes", "progress_percentage"]

    def get_progress_percentage(self, obj):
        user = self.context["request"].user
        total_lectures = obj.lectures.count()
        if total_lectures == 0: return 0
        completed = LecturesProgress.objects.filter(user=user, lecture__section=obj, is_completed=True).count()
        return round((completed / total_lectures) * 100)

class StudentQuizQuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "order", "options"]
    
    def get_options(self, obj):
        # Securely return options without is_correct field
        return [{"id": o.id, "text": o.text, "order": o.order} for o in obj.options.all()]