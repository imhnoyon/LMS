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




#  Dashboard Serializers
class CourseShortSerializer(serializers.ModelSerializer):
    thumbnail = serializers.ImageField(source="advance_info.thumbnail", read_only=True)
    course_progress = serializers.SerializerMethodField()
    class Meta:
        model = Course
        fields = ["id", "title",'subtitle', "thumbnail", "price",'course_progress']
        
    def get_course_progress(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return 0

        if Enrollment.objects.filter(user=user, course=obj).exists():
            return obj.get_progress_percentage(user)

        return 0
       
         
class InvoiceDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "name", "invoice_id", 'payment_method', "amount", "status", "invoice_date", "created_at"]
        
        
class RecentQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ["user", "course_name", "correct_answers", "total_questions", "score_percentage", "submitted_at"]
        
    
        
class StudentDashboardSerializer(serializers.Serializer):
    enrolled_courses_count = serializers.IntegerField()
    active_courses_count = serializers.IntegerField()
    completed_courses_count = serializers.IntegerField()
    recently_enrolled = CourseShortSerializer(many=True)
    recent_invoices = InvoiceDashboardSerializer(many=True)
    recent_quizes = RecentQuizSerializer(many=True)
    

    

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
    
    
    
from .models import Student   
class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'avatar']
        read_only_fields = ['email']


class StudentProfileSerializer(serializers.ModelSerializer):
    user = StudentSerializer()

    class Meta:
        model = Student
        fields = [
            'id',
            'title',
            'date_of_birth',
            'gender',
            'bio',
            'user'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                if attr == "email":
                    continue
                setattr(user, attr, value)
            user.save()

        return instance
    
    
    
 # Enrollment course list
class EnrollCourseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.advance_info.thumbnail", read_only=True)
    course_price=serializers.DecimalField(source="course.price",max_digits=10,decimal_places=2,read_only=True)
    course_progress = serializers.SerializerMethodField()    
    class Meta:
        model = Enrollment
        fields = [
            'id', 
            'course', 
            'course_title', 
            'course_price',
            'course_thumbnail', 
            'is_active', 
            'is_completed', 
            'is_started',
            'course_progress',
            'enrolled_at'
        ]

    def get_course_progress(self, obj):
        # obj is Enrollment, we need Course and User
        user = obj.user
        course = obj.course
        if not user or not course:
            return 0
        return course.get_progress_percentage(user)
    
    
    
# exam & asssessment
class lectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = ['id', 'name', 'order']
        
class sectionSerializer(serializers.ModelSerializer):
    lectures = lectureSerializer(many=True, read_only=True)
    class Meta:
        model = Section
        fields = ['id', 'name', 'order', 'lectures']
        
class ExamAssessmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.advance_info.thumbnail", read_only=True)
    course_price=serializers.DecimalField(source="course.price",max_digits=10,decimal_places=2,read_only=True)
    course_progress = serializers.SerializerMethodField()
    instructor = serializers.CharField(source="course.instructor.name", read_only=True)   
    section_count = serializers.SerializerMethodField()
    lecture_count = serializers.SerializerMethodField() 
    completed_lecture_count = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 
            'course', 
            'instructor',
            'course_title', 
            'course_price',
            'course_thumbnail', 
            'is_active', 
            'is_completed', 
            'is_started',
            'section_count',
            'lecture_count',
            'completed_lecture_count',
            'course_progress',
            'enrolled_at'
        ]

    def get_course_progress(self, obj):
        # obj is Enrollment, we need Course and User
        user = obj.user
        course = obj.course
        if not user or not course:
            return 0
        return course.get_progress_percentage(user)
    
    def get_section_count(self, obj):
        return obj.course.sections.count()
    
    def get_lecture_count(self, obj):
        from apps.courses.models import Lecture
        return Lecture.objects.filter(section__course=obj.course).count()

    def get_completed_lecture_count(self, obj):
        from apps.courses.models import LecturesProgress
        return LecturesProgress.objects.filter(
            user=obj.user, 
            course=obj.course, 
            is_completed=True
        ).count()
        
    
        
        
        

        
    