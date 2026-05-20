from django.urls import path
from apps.analytics import views


# Analytics app URLs
urlpatterns = [
	path("ai/chat/", views.CourseAssistantChatAPIView.as_view(), name="analytics-ai-chat"),
	path("ai/chat/<int:conversation_id>/", views.CourseAssistantChatAPIView.as_view(), name="analytics-ai-chat"),
	path("ai/course-structure/", views.CourseStructureAPIView.as_view(), name="analytics-ai-course-structure"),
	path("ai/lesson-draft/", views.LessonDraftAPIView.as_view(), name="analytics-ai-lesson-draft"),
	path("ai/quiz-questions/", views.QuizQuestionsAPIView.as_view(), name="analytics-ai-quiz-questions"),
	path("ai/improve-content/", views.ContentImprovementAPIView.as_view(), name="analytics-ai-improve-content"),
	path("ai/learning-objectives/", views.LearningObjectivesAPIView.as_view(), name="analytics-ai-learning-objectives"),
	path("ai/courses/", views.OpenAiCourseListView.as_view(), name="analytics-ai-courses"),
]