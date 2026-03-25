from django.urls import path
from . import views

urlpatterns = [
    # Admin can create categories (for now, we can create them via admin panel)
    path('categories/', views.CategoryAPIView.as_view()),
    
    # Basic info
    path('courses/', views.CourseCreateView.as_view()),
    path('courses/<int:pk>/', views.CourseCreateView.as_view()),
    # Advance info
    path('courses/advance/<int:pk>/', views.CourseAdvanceView.as_view()),
    
    
    
    # Outcomes & Requirements
    # path('courses/outcomes/<int:pk>/', views.OutcomeView.as_view()),
    # path('courses/<int:pk>/outcomes/<int:outcome_id>/', views.OutcomeView.as_view()),
    # path('courses/requirements/<int:pk>/', views.RequirementView.as_view()),
    # path('courses/<int:pk>/requirements/<int:req_id>/', views.RequirementView.as_view()),
    # # Curriculum
    # path('courses/<int:pk>/sections/', views.SectionView.as_view()),
    # path('courses/<int:pk>/sections/<int:section_id>/', views.SectionView.as_view()),
    # path('sections/<int:section_id>/lectures/', views.LectureView.as_view()),
    # path('sections/<int:section_id>/lectures/<int:lecture_id>/', views.LectureView.as_view()),
    # path('lectures/<int:lecture_id>/video/', views.LectureVideoView.as_view()),
    # # Quiz
    # path('sections/<int:section_id>/quizzes/', views.QuizView.as_view()),
    # # Publish
    # path('courses/<int:pk>/publish/', views.PublishCourseView.as_view()),
    
    
    
]