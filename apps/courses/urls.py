from django.urls import path
from . import views

urlpatterns = [
    # Admin can create categories (for now, we can create them via admin panel)
    path('categories/', views.CategoryAPIView.as_view()),
    path('courses-list/', views.CourseListView.as_view(), name='course-list'),
    path('courses-lists/', views.CourseListapiView.as_view(), name='course-list'),
    path('courses-list/<int:pk>/', views.courseDetail.as_view(), name='course-list'),
    path('coursesAdmin/review-history/', views.courseAdminReviewHistoryView.as_view(), name='course-admin-review-history'),
    path('course-block-unblock/<int:pk>/', views.CourseBlockUnblockView.as_view(), name='course-block-unblock'),
    # Instructor Deshboard
    path('courses-list-instructor/',views.CourseListByInstructorView.as_view(), name='course-list-instructor'),
    
    
    # Basic info
    path('courses/', views.CourseCreateView.as_view()),
    path('courses/<int:pk>/', views.CourseCreateView.as_view()),
    # Advance info & Outcomes & Requirements
    path('courses/advance-info/<int:pk>/', views.CourseAdvanceInfoManageView.as_view(), name='course-advance-info'),
    
    # Curriculum
    path('courses/sections/<int:pk>/', views.SectionView.as_view()),
    
    path('courses/<int:pk>/sections/<int:section_id>/', views.SectionView.as_view()),
    
    path('sections/lectures/<int:section_id>/', views.LectureView.as_view()),
    path('sections/lectures/<int:section_id>/<int:lecture_id>/', views.LectureView.as_view()),
  
    # Quiz
    path('sections/quizzes/<int:section_id>/', views.QuizView.as_view()),
    path('sections/quizzes/<int:section_id>/<int:quiz_id>/', views.QuizView.as_view()),
    # Publish
    path('courses/publish/<int:pk>/', views.PublishCourseView.as_view()),
    path("courses/<int:course_id>/overview/", views.CourseOverviewAPIView.as_view()),
    
    # Live Classes
    path('live-classes/stats/', views.InstructorLiveClassStatsView.as_view(), name='live-class-stats'),
    path('live-classes/<int:course_id>/', views.LiveClassManageView.as_view(), name='live-class-manage'),
    path('joint-class/<int:id>/', views.MarkLiveClassPresentAPIView.as_view(), name='live-class-manage'),
    
    
    # Student Home pages
    path('home/courses/', views.CourseHomeListView.as_view(), name='student-home-courses'),
    path('home/courses/list/', views.CoursesHomeView.as_view(), name='student-home-courses'),
    
    path('course/info/', views.CourseInformationAPIView.as_view(), name='course-information'),
    path('lectures/comments/', views.CommentLectureAPIView.as_view(), name='course-comments'),
    path('lectures/comments/<int:lecture_id>/', views.CommentLectureAPIView.as_view(), name='course-comments'),
    
    #course details page for instructor
    path("my-courses/<int:pk>/", views.MyCourseDetailsAPIView.as_view()),
    path('courses/<int:course_id>/sections/', views.CourseSectionAPIView.as_view()),

]