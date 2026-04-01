from django.urls import path
from .views import *

urlpatterns = [
    # 🔹 Student Dashboard (from user base)
    path("dashboard/", StudentDashboardView.as_view(), name="student-dashboard"),

    # 🔹 Course Player (Udemy Clone)
    path("courses/<int:course_id>/player/", CoursePlayerView.as_view(), name="course-player"),
    path("courses/<int:course_id>/player/<int:lecture_id>/", CoursePlayerView.as_view(), name="course-player-lecture"),
    path("lectures/<int:lecture_id>/complete/", CompleteLectureView.as_view(), name="complete-lecture"),

    # 🔹 Quiz Attendance
    path("quizzes/<int:quiz_id>/", StudentQuizView.as_view(), name="student-quiz-take"),
    path("quizzes/<int:quiz_id>/submit/", QuizSubmissionView.as_view(), name="student-quiz-submit"),
]