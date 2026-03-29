from django.urls import path
from . import views

urlpatterns = [
    # Admin can create categories (for now, we can create them via admin panel)
    path('categories/', views.CategoryAPIView.as_view()),
    path('courses-list/', views.CourseListView.as_view(), name='course-list'),
    path('courses-list/<int:pk>/', views.courseDetail.as_view(), name='course-list'),
    
    
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
  
    # Quiz
    path('sections/quizzes/<int:section_id>/', views.QuizView.as_view()),
    # Publish
    path('courses/publish/<int:pk>/', views.PublishCourseView.as_view()),
    
    
    
    
]