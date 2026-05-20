"""Analytics app AI integration views.

These endpoints expose the LearnHub AI service functions through DRF APIViews
without modifying the AI module itself. Each endpoint validates its request,
loads the requested course from the existing project models, checks access,
and then calls the relevant AI helper.
"""

from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.courses.models import Course
from apps.courses.serializers import CourseDetailSerializer
from apps.enrollments.models import Enrollment
from apps.orders.models import OrderItem
from apps.organizations.models import Contract, Membership
from LearnHub_AI.services.ai_service import (
    chat_with_assistant,
    suggest_course_structure,
    generate_lesson_draft,
    create_quiz_questions,
    improve_content,
    generate_learning_objectives,
)
from utils.api_response import APIResponse
from utils.paginations import CustomPagination

from .serializers import (
    AIChatConversationDetailSerializer,
    AIChatConversationListSerializer,
    AIChatMessageSerializer,
    AnalyticsCourseListSerializer,
    ChatHistoryQuerySerializer,
    CourseAssistantRequestSerializer,
    CourseStructureRequestSerializer,
    LessonDraftRequestSerializer,
    QuizQuestionsRequestSerializer,
    ContentImprovementRequestSerializer,
    LearningObjectivesRequestSerializer,
)
from .models import AIChatConversation, AIChatMessage


def _can_access_course(user, course: Course) -> bool:
    """Keep course access consistent with the existing project rules."""
    if user.is_superuser or getattr(user, "role", None) == "owner":
        return True

    if course.instructor_id == user.id:
        return True

    if course.organization_id and Membership.objects.filter(
        organization_id=course.organization_id,
        user=user,
        status=Membership.Status.ACTIVE,
        role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER],
    ).exists():
        return True

    if Contract.objects.filter(
        course=course,
        instructor__user=user,
        instructor__status=Membership.Status.ACTIVE,
        instructor__role=Membership.Role.INSTRUCTOR,
    ).exists():
        return True

    return False


def _load_course_for_ai(request, course_id: int):
    """Fetch a course and return a serializer-ready dict for AI prompts."""
    course = (
        Course.objects.select_related("instructor", "organization", "advance_info")
        .prefetch_related("sections__lectures", "outcomes", "requirements")
        .filter(pk=course_id)
        .first()
    )

    if not course:
        return None, APIResponse.error(
            message="Course not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_course(request.user, course):
        return None, APIResponse.error(
            message="You do not have permission to access this course.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return CourseDetailSerializer(course, context={"request": request}).data, None


class BaseCourseAIView(APIView):
    """Base view for all AI endpoints in analytics."""

    permission_classes = [IsAuthenticated]
    request_serializer_class = None

    def get_validated_request_data(self, request):
        serializer = self.request_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def get_course_context(self, request, course_id: int):
        return _load_course_for_ai(request, course_id)


class CourseAssistantChatAPIView(BaseCourseAIView):
    """POST chat messages for a selected course.

    Calls: LearnHub_AI.services.ai_service.chat_with_assistant(course, conversation_history, user_message)
    """

    request_serializer_class = CourseAssistantRequestSerializer

    def get(self, request):
        query_serializer = ChatHistoryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data

        course_id = data.get("course_id")
        conversation_id = data.get("conversation_id")

        if conversation_id:
            conversation = (
                AIChatConversation.objects.filter(id=conversation_id, user=request.user)
                .select_related("course")
                .prefetch_related("messages")
                .first()
            )
            if not conversation:
                return APIResponse.error(
                    message="Conversation not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if not _can_access_course(request.user, conversation.course):
                return APIResponse.error(
                    message="You do not have permission to access this conversation.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            messages = conversation.messages.order_by("-created_at", "-id")
            serializer = AIChatMessageSerializer(messages, many=True)
            return APIResponse.success(
                message="Conversation retrieved successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        conversations = AIChatConversation.objects.filter(user=request.user).select_related("course")
        if course_id:
            conversations = conversations.filter(course_id=course_id)

        conversations = conversations.order_by("-updated_at")
        serializer = AIChatConversationListSerializer(conversations, many=True)

        return APIResponse.success(
            message="Conversation list retrieved successfully.",
            data={
                "count": conversations.count(),
                "results": serializer.data,
            },
            status_code=status.HTTP_200_OK,
        )

    def post(self, request):
        data = self.get_validated_request_data(request)
        course, error = self.get_course_context(request, data["course_id"])
        if error:
            return error

        conversation_id = data.get("conversation_id")
        if conversation_id:
            conversation = AIChatConversation.objects.filter(
                id=conversation_id,
                user=request.user,
                course_id=data["course_id"],
            ).first()
            if not conversation:
                return APIResponse.error(
                    message="Conversation not found for this user and course.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = AIChatConversation.objects.filter(
                user=request.user,
                course_id=data["course_id"],
            ).order_by("-updated_at").first()

            if not conversation:
                conversation = AIChatConversation.objects.create(
                    user=request.user,
                    course_id=data["course_id"],
                    title=(data["user_message"][:100] or "New chat"),
                )

        stored_history = list(
            conversation.messages.order_by("created_at", "id").values("role", "content")
        )

        # Backward compatibility: if DB has no prior messages, allow client-sent
        # conversation history to seed the assistant context.
        ai_history = stored_history if stored_history else data.get("conversation_history", [])

        try:
            response_text = chat_with_assistant(
                course=course,
                conversation_history=ai_history,
                user_message=data["user_message"],
            )
        except Exception as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            AIChatMessage.objects.create(
                conversation=conversation,
                role=AIChatMessage.Role.USER,
                content=data["user_message"],
            )
            assistant_message = AIChatMessage.objects.create(
                conversation=conversation,
                role=AIChatMessage.Role.ASSISTANT,
                content=response_text,
            )

            if not conversation.title:
                conversation.title = data["user_message"][:100] or "New chat"
            conversation.save(update_fields=["title", "updated_at"])

        return APIResponse.success(
            message="AI chat response generated successfully.",
            data={
                "course_id": data["course_id"],
                "conversation_id": conversation.id,
                "assistant_message_id": assistant_message.id,
                "response": response_text,
            },
            status_code=status.HTTP_200_OK,
        )


class CourseStructureAPIView(BaseCourseAIView):
    """POST course metadata to generate a recommended structure.

    Calls: LearnHub_AI.services.ai_service.suggest_course_structure(course)
    """

    request_serializer_class = CourseStructureRequestSerializer

    def post(self, request):
        data = self.get_validated_request_data(request)
        course, error = self.get_course_context(request, data["course_id"])
        if error:
            return error

        try:
            response_text = suggest_course_structure(course)
        except Exception as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return APIResponse.success(
            message="Course structure suggestion generated successfully.",
            data={
                "course_id": data["course_id"],
                "response": response_text,
            },
            status_code=status.HTTP_200_OK,
        )


class LessonDraftAPIView(BaseCourseAIView):
    """POST lecture details to generate a lesson draft.

    Calls: LearnHub_AI.services.ai_service.generate_lesson_draft(course, lecture_name, lecture_notes)
    """

    request_serializer_class = LessonDraftRequestSerializer

    def post(self, request):
        data = self.get_validated_request_data(request)
        course, error = self.get_course_context(request, data["course_id"])
        if error:
            return error

        try:
            response_text = generate_lesson_draft(
                course=course,
                lecture_name=data["lecture_name"],
                lecture_notes=data.get("lecture_notes", ""),
            )
        except Exception as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return APIResponse.success(
            message="Lesson draft generated successfully.",
            data={
                "course_id": data["course_id"],
                "lecture_name": data["lecture_name"],
                "response": response_text,
            },
            status_code=status.HTTP_200_OK,
        )


class QuizQuestionsAPIView(BaseCourseAIView):
    """POST topic information to generate quiz questions.

    Calls: LearnHub_AI.services.ai_service.create_quiz_questions(course, topic, num_questions)
    """

    request_serializer_class = QuizQuestionsRequestSerializer

    def post(self, request):
        data = self.get_validated_request_data(request)
        course, error = self.get_course_context(request, data["course_id"])
        if error:
            return error

        try:
            response_text = create_quiz_questions(
                course=course,
                topic=data["topic"],
                num_questions=data.get("num_questions", 5),
            )
        except Exception as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return APIResponse.success(
            message="Quiz questions generated successfully.",
            data={
                "course_id": data["course_id"],
                "topic": data["topic"],
                "num_questions": data.get("num_questions", 5),
                "response": response_text,
            },
            status_code=status.HTTP_200_OK,
        )


class ContentImprovementAPIView(BaseCourseAIView):
    """POST existing content and a goal to improve the content.

    Calls: LearnHub_AI.services.ai_service.improve_content(course, content_to_improve, improvement_goal)
    """

    request_serializer_class = ContentImprovementRequestSerializer

    def post(self, request):
        data = self.get_validated_request_data(request)
        course, error = self.get_course_context(request, data["course_id"])
        if error:
            return error

        try:
            response_text = improve_content(
                course=course,
                content_to_improve=data["content_to_improve"],
                improvement_goal=data["improvement_goal"],
            )
        except Exception as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return APIResponse.success(
            message="Content improved successfully.",
            data={
                "course_id": data["course_id"],
                "response": response_text,
            },
            status_code=status.HTTP_200_OK,
        )


class LearningObjectivesAPIView(BaseCourseAIView):
    """POST a course or section scope to generate learning objectives.

    Calls: LearnHub_AI.services.ai_service.generate_learning_objectives(course, section_name)
    """

    request_serializer_class = LearningObjectivesRequestSerializer

    def post(self, request):
        data = self.get_validated_request_data(request)
        course, error = self.get_course_context(request, data["course_id"])
        if error:
            return error

        try:
            response_text = generate_learning_objectives(
                course=course,
                section_name=data.get("section_name", ""),
            )
        except Exception as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return APIResponse.success(
            message="Learning objectives generated successfully.",
            data={
                "course_id": data["course_id"],
                "section_name": data.get("section_name", ""),
                "response": response_text,
            },
            status_code=status.HTTP_200_OK,
        )
        
        
        
        
# Course list details page for instructor and Organization

class OpenAiCourseListView(APIView):
    permission_classes = [IsAuthenticated, ]
    paginator_class = CustomPagination

    def get(self, request):
        courses = Course.objects.select_related("instructor", "organization").prefetch_related(
            "sections__lectures",
            "sections__quizzes",
            "sections__lectures__quiz",
        ).order_by('-id')

        user_role = getattr(request.user, "role", None)

        if user_role == "student":
            enrolled_course_ids = Enrollment.objects.filter(
                user=request.user,
                is_active=True,
            ).values_list("course_id", flat=True)

            purchased_course_ids = OrderItem.objects.filter(
                order__user=request.user,
                order__status="paid",
            ).values_list("course_id", flat=True).distinct()

            accessible_course_ids = set(enrolled_course_ids) | set(purchased_course_ids)
            courses = courses.filter(id__in=accessible_course_ids)

        elif user_role == "Or_admin":
            organization_ids = Membership.objects.filter(
                user=request.user,
                status=Membership.Status.ACTIVE,
                role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER],
            ).values_list("organization_id", flat=True)
            courses = courses.filter(organization_id__in=organization_ids)
        elif user_role == "instructor":
            courses = courses.filter(instructor=request.user)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = AnalyticsCourseListSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)