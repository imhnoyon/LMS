from django.urls import path
from .views import *

urlpatterns = [
    # 🔹 Student Dashboard (from user base)
    path("dashboard/", StudentDashboardView.as_view(), name="student-dashboard"),

    # 🔹 Course Player 
    path("courses/<int:course_id>/player/", CoursePlayerView.as_view(), name="course-player"),
    path("courses/<int:course_id>/player/<int:lecture_id>/", CoursePlayerView.as_view(), name="course-player-lecture"),
    path("lectures/<int:lecture_id>/complete/", CompleteLectureView.as_view(), name="complete-lecture"),

    # 🔹 Quiz Attendance
    path("quizzes/<int:quiz_id>/", StudentQuizView.as_view(), name="student-quiz-take"),
    path("quizzes/<int:quiz_id>/submit/", QuizSubmissionView.as_view(), name="student-quiz-submit"),
    
    
    # 🔹 Student Profile
    path("profile/", StudentProfileUpdateView.as_view(), name="student-profile-update"),
    path('enroll-courses/', EnrollCourseAPIView.as_view(), name='enroll-course'),
    
    path('exam-assessments-courses/', ExamAssessmentAPIView.as_view(), name='enroll-course'),
    path('course-completed/<int:course_id>/', CheckCourseCompletionView.as_view(), name='check-course-completion'),
    
    #review 
    path('reviews/<int:course_id>/', CreateReviewView.as_view(), name='course-reviews'),
    path('reviews-updated/<int:review_id>/', CreateReviewView.as_view(), name='course-reviews'),
    path('review-list/', ReviewListAPIView.as_view(), name='delete-review'),
    
    # quiz attempts-list
    path('quiz-attempts-list/', CourseQuizAttemptListAPIView.as_view(), name='quiz-attempts-list'),
    
    #purchase-history
    path('student/purchase-history/', CoursePurchaseHistoryAPIView.as_view(), name='purchase-history'),
    
    #password reset
    path('password-reset/', ChangePasswordAPIView.as_view(), name='password-reset'),
    
    #delete account
     path("delete-account/", DeleteAccountAPIView.as_view(), name="delete-account"),
     
     
    # live classes
    path('student/live-classes/upcoming/',StudentLiveClassListView.as_view(),name='student-upcoming-live-class-list'),
    path('joint-live-class/<int:live_class_id>/',JoinLiveClassView.as_view(),name='joint-live-class'),
    
    
    
    
]