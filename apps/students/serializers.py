from rest_framework import serializers
from apps.users.models import User
from apps.enrollments.models import Enrollment, Certificate
from apps.payments.models import Invoice
from apps.courses.models import *
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




from apps.students.models import Student

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'avatar']
        read_only_fields = ['id', 'email']

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer()

    class Meta:
        model = Student
        fields = ['id', 'title', 'date_of_birth', 'gender', 'bio', 'user']
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


class StudentDashboardSerializer(serializers.Serializer):
    enrolled_courses_count = serializers.IntegerField()
    active_courses_count = serializers.IntegerField()
    completed_courses_count = serializers.IntegerField()


class EnrollCourseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.advance_info.thumbnail", read_only=True)
    course_price = serializers.DecimalField(source="course.price", max_digits=10, decimal_places=2, read_only=True)
    instructor = serializers.CharField(source="course.instructor.name", read_only=True)
    
    # 🔹 PROGRESS FIELDS
    total_lectures = serializers.SerializerMethodField()
    completed_lectures = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id", "course", "course_title", "course_thumbnail", "course_price", "instructor",
            "is_active", "is_completed", "is_started", "enrolled_at",
            "total_lectures", "completed_lectures", "progress_percentage"
        ]

    def get_total_lectures(self, obj):
        return Lecture.objects.filter(section__course=obj.course).count()

    def get_completed_lectures(self, obj):
        return LecturesProgress.objects.filter(user=obj.user, is_completed=True, lecture__section__course=obj.course).count()

    def get_progress_percentage(self, obj):
        total = self.get_total_lectures(obj)
        if total == 0: return 0
        completed = self.get_completed_lectures(obj)
        return round((completed / total) * 100)


class LecturePlayerSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    is_accessible = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = ["id", "name", "description", "video_file", "note_file", "is_completed", "is_accessible"]

    def get_is_completed(self, obj):
        user = self.context.get("request").user
        return LecturesProgress.objects.filter(user=user, lecture=obj, is_completed=True).exists()

    def get_is_accessible(self, obj):
        user = self.context.get("request").user
        return is_lecture_accessible(user, obj)


class QuizPlayerSerializer(serializers.ModelSerializer):
    is_passed = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "questions_count", "is_passed"]

    def get_is_passed(self, obj):
        user = self.context.get("request").user
        return is_quiz_passed(user, obj)

    def get_questions_count(self, obj):
        return obj.questions.count()


class SectionPlayerSerializer(serializers.ModelSerializer):
    lectures = LecturePlayerSerializer(many=True, read_only=True)
    quizzes = QuizPlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ["id", "name", "lectures", "quizzes"]


class CoursePlayerSerializer(serializers.ModelSerializer):
    sections = SectionPlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ["id", "title", "sections"]


# --- Assessment Dashboards ---

class ExamLectureSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    
    class Meta:
        model = Lecture
        fields = ["id", "name", "is_completed"]
        
    def get_is_completed(self, obj):
        user = self.context.get('request').user
        return LecturesProgress.objects.filter(user=user, lecture=obj, is_completed=True).exists()

class ExamSectionSerializer(serializers.ModelSerializer):
    lectures = ExamLectureSerializer(many=True, read_only=True)
    
    class Meta:
        model = Section
        fields = ["id", "name", "lectures"]

class ExamAssessmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.advance_info.thumbnail", read_only=True)
    instructor = serializers.CharField(source="course.instructor.name", read_only=True)
    
    # Hierarchy
    sections = ExamSectionSerializer(source="course.sections", many=True, read_only=True)
    
    # Progress Metrics
    section_count = serializers.SerializerMethodField()
    lecture_count = serializers.SerializerMethodField()
    completed_lecture_count = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id", "course", "course_title", "course_thumbnail", "instructor",
            "is_completed", "enrolled_at", "sections",
            "section_count", "lecture_count", "completed_lecture_count"
        ]

    def get_section_count(self, obj):
        return obj.course.sections.count()

    def get_lecture_count(self, obj):
        return Lecture.objects.filter(section__course=obj.course).count()

    def get_completed_lecture_count(self, obj):
        return LecturesProgress.objects.filter(
            user=obj.user, 
            lecture__section__course=obj.course, 
            is_completed=True
        ).count()


class CertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.user.name', read_only=True)

    class Meta:
        model = Certificate
        fields = ["id",'student_name', "issue_date", "certificate_id"]
        
        
        
# Course Review serializers
class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='user.name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'course',
            'course_title',
            'user',
            'student_name',
            'rating',
            'comment',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'course', 'created_at', 'updated_at']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

        
        
class ReviewListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='user.name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id',
            'course',
            'course_title',
            'user',
            'student_name',
            'rating',
            'comment',
            'avatar',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'course', 'created_at', 'updated_at']

    def get_avatar(self, obj):
        request = self.context.get("request")
        if hasattr(obj.user, 'avatar') and obj.user.avatar:
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None

        
    
class CourseQuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ["id", "user",'course','quiz', "course_name", "correct_answers", "total_questions", "score_percentage", "submitted_at"]    
        
    

class CoursePurchasesHistory(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.advance_info.thumbnail", read_only=True)
    course_price=serializers.DecimalField(source="course.price",max_digits=10,decimal_places=2,read_only=True)
    instructor = serializers.CharField(source="course.instructor.name", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 
            'course', 
            'instructor',
            'course_title', 
            'course_price',
            'course_thumbnail', 
            'enrolled_at'
        ]



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "New password and confirm password do not match."
            })
        return attrs
    
    
    
class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    
    
class LiveClassStudentSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveClass
        fields = [
            'id',
            'title',
            'topic',
            'instructor',
            'instructor_name',
            'course',
            'course_title',
            'scheduled_date',
            'scheduled_time',
            'duration_minutes',
            'platform',
            'class_link',
            'is_recorded',
            'recording_link',
            'status',
            'created_at',
        ]
    
    def get_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return "Missed"
            
        from apps.courses.models import LiveClassAttendance
        if LiveClassAttendance.objects.filter(live_class=obj, student=request.user).exists():
            return "Attended"
        return "Missed"
    
    
# live session recording videos serializers

class LiveRecordingVideo(serializers.ModelSerializer):
        class Meta:
            model = sessionRecordUploader
            fields = ["id","course_name", "title", "recording_file", "uploaded_at"]
            read_only_fields = ["id", "course_name", "title", "uploaded_at"]
    
    
        
        
    