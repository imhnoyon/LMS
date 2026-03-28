from rest_framework import serializers
from .models import *
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
            'language', 'level', 'price', 'discount_price',
            'coupon_code', 'expiry_type', 'status'
        ]
        read_only_fields = ['id', 'status']


# Advance Information serializers
class CourseOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcome
        fields = ['id', 'text', 'order']

class CourseRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRequirement
        fields = ['id', 'text', 'order']

class CourseAdvanceInfoSerializer(serializers.ModelSerializer):
    outcomes = serializers.SerializerMethodField(read_only=True)
    requirements = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseAdvanceInfo
        fields = ['id', 'thumbnail', 'trailer_video', 'description', 'outcomes', 'requirements']

    def get_outcomes(self, instance):
        return CourseOutcomeSerializer(instance.course.outcomes.all(), many=True).data

    def get_requirements(self, instance):
        return CourseRequirementSerializer(instance.course.requirements.all(), many=True).data

    def _process_nested_items(self, course, data_list, model_class):
        if data_list is None:
            return
        
        # If it's a string (common in multipart forms), try to parse it
        if isinstance(data_list, str):
            try:
                data_list = json.loads(data_list)
            except (json.JSONDecodeError, TypeError):
                data_list = []

        if not isinstance(data_list, list):
            data_list = [data_list] if data_list else []

        # Clear existing
        model_class.objects.filter(course=course).delete()
        
        for i, item in enumerate(data_list):
            if isinstance(item, str):
                model_class.objects.create(course=course, text=item, order=i)
            elif isinstance(item, dict):
                text = item.get('text')
                if text:
                    model_class.objects.create(course=course, text=text, order=item.get('order', i))

    def update(self, instance, validated_data):
        # Access raw data from the request because the serializer might filter out non-model fields
        request = self.context.get('request')
        outcomes_data = request.data.get('outcomes') if request else None
        requirements_data = request.data.get('requirements') if request else None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._process_nested_items(instance.course, outcomes_data, CourseOutcome)
        self._process_nested_items(instance.course, requirements_data, CourseRequirement)
        
        return instance

    def create(self, validated_data):
        request = self.context.get('request')
        outcomes_data = request.data.get('outcomes') if request else None
        requirements_data = request.data.get('requirements') if request else None
        
        course = validated_data.get('course')
        advance_info = CourseAdvanceInfo.objects.create(**validated_data)
        
        self._process_nested_items(course, outcomes_data, CourseOutcome)
        self._process_nested_items(course, requirements_data, CourseRequirement)
        
        return advance_info


# Lecture
class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = ['id', 'name', 'order', 'description', 'video_file', 'LectureAttachment', 'LectureNoteFile',]


class SectionSerializer(serializers.ModelSerializer):
    lectures = LectureSerializer(many=True, read_only=True)
    class Meta:
        model = Section
        fields = ['id', 'name', 'order', 'lectures']



class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']

class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, required=False)
    class Meta:
        model = Question
        fields = ['id', 'question_type', 'text', 'order', 'options']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'time_limit_minutes', 
            'attempts_allowed', 'passing_score', 'shuffle_questions', 'questions'
        ]



# Course details serializers
class CourseAdvanceInfoDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAdvanceInfo
        fields = ['id', 'thumbnail', 'trailer_video', 'description']
        
class CourseOutcomeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcome
        fields = ['id', 'text', 'order']

class CourseRequirementDetailSerializer(serializers.ModelSerializer):
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
        
class CourseDetailSerializer(serializers.ModelSerializer):
    advance_info = CourseAdvanceInfoDetailSerializer(read_only=True)
    outcomes = CourseOutcomeDetailSerializer(many=True, read_only=True)
    requirements = CourseRequirementDetailSerializer(many=True, read_only=True)
    sections = SectionDetailSerializer(many=True, read_only=True)
 
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'subtitle', 'category', 'topic', 'language', 'level', 'price','rating', 'discount_price', 'coupon_code', 'expiry_type', 'status','advance_info', 'outcomes','requirements','sections'] 
        
# Course details serializers ended here
        
        
