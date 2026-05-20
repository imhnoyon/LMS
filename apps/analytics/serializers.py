from rest_framework import serializers

from apps.courses.models import Course
from .models import AIChatConversation, AIChatMessage


class BaseCourseAIRequestSerializer(serializers.Serializer):
	course_id = serializers.IntegerField(min_value=1)


class CourseAssistantRequestSerializer(BaseCourseAIRequestSerializer):
	user_message = serializers.CharField(allow_blank=False, trim_whitespace=True)
	conversation_id = serializers.IntegerField(required=False, min_value=1)
	conversation_history = serializers.ListField(
		child=serializers.DictField(),
		required=False,
		default=list,
	)


class ChatHistoryQuerySerializer(serializers.Serializer):
	course_id = serializers.IntegerField(required=False, min_value=1)
	conversation_id = serializers.IntegerField(required=False, min_value=1)
	limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class AIChatMessageSerializer(serializers.ModelSerializer):
	sender = serializers.SerializerMethodField()
	sender_name = serializers.SerializerMethodField()
	body = serializers.CharField(source="content", read_only=True)
	status = serializers.SerializerMethodField()
	is_read = serializers.SerializerMethodField()
	conversation = serializers.IntegerField(source="conversation_id", read_only=True)

	class Meta:
		model = AIChatMessage
		fields = ["id", "conversation", "sender", "sender_name", "body", "status", "is_read", "created_at"]

	def get_sender(self, obj):
		if obj.role == AIChatMessage.Role.USER:
			return str(obj.conversation.user_id)
		return "00000000-0000-0000-0000-000000000000"

	def get_sender_name(self, obj):
		if obj.role == AIChatMessage.Role.USER:
			return getattr(obj.conversation.user, "name", "") or "User"
		return "AI Assistant"

	def get_status(self, obj):
		return "sent"

	def get_is_read(self, obj):
		return False


class AIChatConversationListSerializer(serializers.ModelSerializer):
	conversation_id = serializers.IntegerField(source="id", read_only=True)
	last_message = serializers.SerializerMethodField()
	last_message_role = serializers.SerializerMethodField()
	message_count = serializers.SerializerMethodField()

	class Meta:
		model = AIChatConversation
		fields = [
			"id",
			"conversation_id",
			"course",
			"title",
			"created_at",
			"updated_at",
			"last_message",
			"last_message_role",
			"message_count",
		]

	def get_last_message(self, obj):
		message = obj.messages.order_by("-created_at", "-id").first()
		if not message:
			return ""
		text = message.content or ""
		return text[:150]

	def get_last_message_role(self, obj):
		message = obj.messages.order_by("-created_at", "-id").first()
		return message.role if message else ""

	def get_message_count(self, obj):
		return obj.messages.count()


class AIChatConversationDetailSerializer(serializers.ModelSerializer):
	messages = AIChatMessageSerializer(many=True, read_only=True)

	class Meta:
		model = AIChatConversation
		fields = ["id", "course", "title", "created_at", "updated_at", "messages"]


class CourseStructureRequestSerializer(BaseCourseAIRequestSerializer):
	pass


class LessonDraftRequestSerializer(BaseCourseAIRequestSerializer):
	lecture_name = serializers.CharField(allow_blank=False, trim_whitespace=True)
	lecture_notes = serializers.CharField(required=False, allow_blank=True, default="")


class QuizQuestionsRequestSerializer(BaseCourseAIRequestSerializer):
	topic = serializers.CharField(allow_blank=False, trim_whitespace=True)
	num_questions = serializers.IntegerField(required=False, default=5, min_value=3, max_value=10)


class ContentImprovementRequestSerializer(BaseCourseAIRequestSerializer):
	content_to_improve = serializers.CharField(allow_blank=False)
	improvement_goal = serializers.CharField(allow_blank=False, trim_whitespace=True)


class LearningObjectivesRequestSerializer(BaseCourseAIRequestSerializer):
	section_name = serializers.CharField(required=False, allow_blank=True, default="")

class AnalyticsCourseListSerializer(serializers.ModelSerializer):
	quizzes = serializers.IntegerField(source="quizzes_count", read_only=True)
	quiz_count = serializers.IntegerField(source="quizzes_count", read_only=True)
	instructor_name = serializers.CharField(source="instructor.name", read_only=True)
	organization_name = serializers.CharField(source="organization.name", read_only=True)
	summary = serializers.SerializerMethodField()

	class Meta:
		model = Course
		fields = [
			"id",
			"title",
			"subtitle",
			"instructor_name",
			"organization_name",
			"quizzes",
			"quiz_count",
			"summary",
		]

	def get_summary(self, obj):
		lecture_names = []
		quiz_names = []
		seen_quiz_ids = set()

		for section in obj.sections.all():
			for lecture in section.lectures.all():
				if lecture.name:
					lecture_names.append(lecture.name)

				quiz = getattr(lecture, "quiz", None)
				if quiz and quiz.id not in seen_quiz_ids and quiz.title:
					seen_quiz_ids.add(quiz.id)
					quiz_names.append(quiz.title)

			for quiz in section.quizzes.all():
				if quiz.id not in seen_quiz_ids and quiz.title:
					seen_quiz_ids.add(quiz.id)
					quiz_names.append(quiz.title)

		return {
			"lectures": lecture_names,
			"quizzes": quiz_names,
		}
