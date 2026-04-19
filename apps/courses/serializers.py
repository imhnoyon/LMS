from rest_framework import serializers

from apps.orders.models import WishlistItem
from .models import *
from apps.instructors.models import Instructor
import json


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'updated_at']


class CourseBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'subtitle', 'category', 'topic',
            'language', 'level', 'price', 'discount_price','duration',
            'coupon_code', 'expiry_type', 'status', 'organization'
        ]
        read_only_fields = ['id', 'status', 'organization']


# Advance Information serializer
import json
from rest_framework import serializers
from .models import (
    CourseAdvanceInfo,
    CourseOutcome as CourseOutcomeModel,
    CourseRequirement as CourseRequirementModel,
)


class CourseOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcomeModel
        fields = ['id', 'text', 'order']


class CourseRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRequirementModel
        fields = ['id', 'text', 'order']


class CourseAdvanceInfoSerializer(serializers.ModelSerializer):
    outcomes = serializers.SerializerMethodField(read_only=True)
    requirements = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseAdvanceInfo
        fields = ['id', 'thumbnail', 'trailer_video', 'description', 'outcomes', 'requirements']

    def get_outcomes(self, instance):
        return CourseOutcomeSerializer(
            instance.course.outcomes.all().order_by('order'),
            many=True
        ).data

    def get_requirements(self, instance):
        return CourseRequirementSerializer(
            instance.course.requirements.all().order_by('order'),
            many=True
        ).data

    def _parse_json_field(self, field_data):
        if not field_data:
            return []

        if isinstance(field_data, str):
            try:
                field_data = json.loads(field_data)
            except json.JSONDecodeError:
                return []

        if isinstance(field_data, dict):
            field_data = [field_data]

        if not isinstance(field_data, list):
            return []

        return field_data

    def _process_nested_items(self, course, data_list, model_class):
        data_list = self._parse_json_field(data_list)

        model_class.objects.filter(course=course).delete()

        items_to_create = []
        auto_order = 1

        for item in data_list:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    items_to_create.append(
                        model_class(
                            course=course,
                            text=text,
                            order=auto_order
                        )
                    )
                    auto_order += 1

            elif isinstance(item, dict):
                text = str(item.get('text', '')).strip()
                if not text:
                    continue

                order = item.get('order')
                if not order:
                    order = auto_order

                items_to_create.append(
                    model_class(
                        course=course,
                        text=text,
                        order=order
                    )
                )
                auto_order += 1

        if items_to_create:
            model_class.objects.bulk_create(items_to_create)

    def create(self, validated_data):
        request = self.context.get('request')
        outcomes_data = request.data.get('outcomes') if request else None
        requirements_data = request.data.get('requirements') if request else None

        advance_info = CourseAdvanceInfo.objects.create(**validated_data)

        self._process_nested_items(
            advance_info.course,
            outcomes_data,
            CourseOutcomeModel
        )
        self._process_nested_items(
            advance_info.course,
            requirements_data,
            CourseRequirementModel
        )

        return advance_info

    def update(self, instance, validated_data):
        request = self.context.get('request')
        outcomes_data = request.data.get('outcomes') if request else None
        requirements_data = request.data.get('requirements') if request else None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if outcomes_data is not None:
            self._process_nested_items(
                instance.course,
                outcomes_data,
                CourseOutcomeModel
            )

        if requirements_data is not None:
            self._process_nested_items(
                instance.course,
                requirements_data,
                CourseRequirementModel
            )

        return instance

# Lecture
class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = ['id', 'name', 'order', 'description', 'video_file', 'LectureAttachment', 'LectureNoteFile','lecture_notes']
           
    def create(self, validated_data):
        section = validated_data.get('section')

        last_lecture = Lecture.objects.filter(section=section).order_by('-order').first()
        next_order = 1 if not last_lecture else last_lecture.order + 1

        validated_data['order'] = next_order
        return super().create(validated_data)
    


class SectionSerializer(serializers.ModelSerializer):
    lectures = LectureSerializer(many=True, read_only=True)
    class Meta:
        model = Section
        fields = ['id', 'name', 'order', 'lectures']



class QuestionOptionSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']



class QuestionSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(read_only=True)
    options = QuestionOptionSerializer(many=True, required=False)
    

    class Meta:
        model = Question
        fields = ['id', 'question_type', 'text', 'order', 'options', ]
        
    


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'time_limit_minutes',
            'attempts_allowed',
            'passing_score',
            'shuffle_questions',
            'questions'
        ]
        
        
    
# Course details serializers
class CourseAdvanceInfoDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAdvanceInfo
        fields = ['id', 'thumbnail', 'trailer_video', 'description']
        
class CourseOutCome(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcome
        fields = ['id', 'text', 'order']

class CourseRequirement(serializers.ModelSerializer):
    class Meta:
        model = CourseRequirement
        fields = ['id', 'text', 'order']

class QuestionOptionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']
        
class SectionDetailSerializer(serializers.ModelSerializer):
    lectures = LectureSerializer(many=True, read_only=True)
    class Meta:
        model = Section
        fields = ['id', 'name', 'order', 'lectures', ]
        
class InstructorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'get_biography','avatar']
        
class CourseDetailSerializer(serializers.ModelSerializer):
    advance_info = CourseAdvanceInfoDetailSerializer(read_only=True)
    outcomes = CourseOutCome(many=True, read_only=True)
    requirements = CourseRequirement(many=True, read_only=True)
    sections = SectionDetailSerializer(many=True, read_only=True)
    instructor = InstructorDetailSerializer(read_only=True)
    modules = serializers.IntegerField(source='sections.count', read_only=True)
    lectures = serializers.IntegerField(read_only=True)
    quizes = serializers.IntegerField(source='quizzes_count', read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    description = serializers.CharField(source='advance_info.description', read_only=True)
    
    related_courses = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title','subtitle', 'Category', 'topic', 'language','description', 'level', 'price','rating','duration', 'discount_price', 'coupon_code','is_wishlisted', 'expiry_type','rating','reviews_count', 'status','modules','lectures','quizes','instructor','advance_info', 'outcomes','requirements','sections', 'related_courses'] 
        
    def get_is_wishlisted(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return WishlistItem.objects.filter(wishlist__user=user, course=obj).exists()
        return False
    
    def get_related_courses(self, obj):
        related = Course.objects.filter(
            category=obj.category
        ).exclude(id=obj.id)[:5]

        return [
            {
                "id": course.id,
                "title": course.title
            }
            for course in related
        ]
        
# Course details serializers ended here


# Live Class Serializers
class LiveClassSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    is_recorded = serializers.BooleanField(required=False)
    
    # 🔹 Override to bypass strict ChoiceField validation

    class Meta:
        model = LiveClass
        fields = [
            'id', 'title', 'instructor', 'instructor_name', 'course', 'course_title',
            'topic', 'scheduled_date', 'scheduled_time','is_present',
            'platform', 'class_link', 'is_recorded',  'created_at'
        ]
        read_only_fields = ['id', 'instructor', 'course', 'created_at']

    def validate_platform(self, value):
        normalized = value.lower().replace(" ", "_")
        
        # Check against actual model choices
        valid_choices = [choice[0] for choice in LiveClass.PLATFORM_CHOICES]
        if normalized not in valid_choices:
            raise serializers.ValidationError(f"Invalid platform. Choose from: {', '.join(valid_choices)}")
            
        return normalized


class LiveClassAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    class_title = serializers.CharField(source='live_class.title', read_only=True)

    class Meta:
        model = LiveClassAttendance
        fields = [
            'id', 'live_class', 'class_title', 'student', 'student_name',
            'status', 'joined_at', 'left_at'
        ]
        read_only_fields = ['id', 'joined_at', 'left_at']


# Course Admin Review History Serializer
class courseReviewHistorySerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    instructor_name = serializers.CharField(source='course.instructor.name', read_only=True)
    reviewer_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = CourseReviewHistory
        fields = ['id', 'course', 'course_title', 'instructor_name', 'reviewer_name', 'status', 'reviewed_at']
        read_only_fields = ['id', 'course', 'user', 'status', 'reviewed_at']
        
        
        
class instructorSerializers(serializers.ModelSerializer):
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    class Meta:
        model = Instructor
        fields = ['id', 'Instructor_name', 'title','biography','avatar']
        
        
    def get_avatar(self, obj):
        if obj.user.avatar:
            return obj.user.avatar.url
        return None
    
    
    
class courseInformationserializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'subtitle']
        
        
        
        
class CommentLectureSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    replies = serializers.SerializerMethodField()
    image = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'lecture', 'user_name', 'text', 'parent', 'replies','image', 'created_at']

    def get_replies(self, obj):
        return CommentLectureSerializer(obj.replies.all(), many=True, context=self.context).data