from rest_framework import serializers
from .models import *



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'created_at',
            'updated_at'
        ]

    



# Step 1: Basic Info
class CourseBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'subtitle', 'category', 'topic',
                  'language', 'level', 'price', 'discount_price',
                  'coupon_code', 'expiry_type']

# Step 2: Advance Info
class CourseOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcome
        fields = ['id', 'text', 'order']

class CourseRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRequirement
        fields = ['id', 'text', 'order']

class CourseAdvanceInfoSerializer(serializers.ModelSerializer):
    outcomes = CourseOutcomeSerializer(many=True, read_only=True)
    requirements = CourseRequirementSerializer(many=True, read_only=True)

    class Meta:
        model = CourseAdvanceInfo
        fields = ['id', 'thumbnail', 'trailer_video','description', 'outcomes', 'requirements']




# Step 3: Curriculum
class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = ['id', 'name', 'order', 'description', 'notes_text']

class SectionSerializer(serializers.ModelSerializer):
    lectures = LectureSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ['id', 'name', 'order', 'lectures']

# Quiz
class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']

class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_type', 'text', 'order', 'options']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'time_limit_minutes',
                  'attempts_allowed', 'passing_score', 'shuffle_questions', 'questions']