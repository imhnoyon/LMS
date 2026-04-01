from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from utils.api_response import APIResponse
from apps.courses.models import *
from apps.payments.models import Invoice
from apps.enrollments.models import Enrollment, Certificate
from .serializers import *
from .helper_funtion import is_lecture_accessible, get_next_lecture, is_quiz_passed
from .models import Student
from rest_framework import status
from rest_framework.generics import get_object_or_404
from utils.permissions import IsStudent
from utils.paginations import CustomPagination


# 🔹 Dashboard Summary
class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        enrollments = Enrollment.objects.filter(user=user)

        enrolled_courses_count = enrollments.count()
        active_courses_count = enrollments.filter(is_started=True).count()
        completed_courses_count = enrollments.filter(is_completed=True).count()
        recently_enrolled = [
            enrollment.course for enrollment in enrollments.order_by("-enrolled_at")[:4]
        ]

        recent_invoices = Invoice.objects.filter(user=user).order_by("-invoice_date", "-created_at")[:10]
        recent_quizes = QuizAttempt.objects.filter(user=user).order_by( "-submitted_at")[:10]
        

        data = {
            "enrolled_courses_count": enrolled_courses_count,
            "active_courses_count": active_courses_count,
            "completed_courses_count": completed_courses_count,
            "recently_enrolled": recently_enrolled,
            "recent_invoices": recent_invoices,
            "recent_quizes": recent_quizes
        }

        serializer = StudentDashboardSerializer(instance=data, context={"request": request})

        return APIResponse.success(
            message="Student dashboard data fetched successfully.",
            data=serializer.data,
            status_code=200
        )


# 🔹 Course Player 
class CoursePlayerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, lecture_id=None):
        course = get_object_or_404(Course, id=course_id)
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course
        ).first()
        
        # Check if student is actually enrolled
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return APIResponse.error(message="You are not enrolled in this course.", status_code=403)
        
        
        # First time course open করলে started true হবে
        if not enrollment.is_started:
            enrollment.is_started = True
            enrollment.save(update_fields=["is_started"])

        sections = course.sections.prefetch_related("lectures", "quizzes").all()
        current_lecture = None

        if lecture_id:
            # Direct access to specific lecture
            requested_lecture = get_object_or_404(Lecture, id=lecture_id, section__course=course)
            if not is_lecture_accessible(request.user, requested_lecture):
                return APIResponse.error(message="Prerequisite content not completed.", status_code=403)
            current_lecture = requested_lecture
        else:
            # Find last incomplete lecture for student
            all_lectures = Lecture.objects.filter(section__course=course).order_by("section__order", "order")
            for lec in all_lectures:
                if not LecturesProgress.objects.filter(user=request.user, lecture=lec, is_completed=True).exists():
                    if is_lecture_accessible(request.user, lec):
                        current_lecture = lec
                        break
            if not current_lecture:
                current_lecture = all_lectures.first()

        next_content = get_next_lecture(current_lecture)
        
        data = {
            "course_title": course.title,
            "course_progress_percentage": course.get_progress_percentage(request.user),
            "current_lecture": {
                "id": current_lecture.id,
                "name": current_lecture.name,
                "description": current_lecture.description,
                "video_file": request.build_absolute_uri(current_lecture.video_file.url) if current_lecture.video_file else None,
                "note_file": request.build_absolute_uri(current_lecture.LectureNoteFile.url) if current_lecture.LectureNoteFile else None,
            },
            "next_lecture": {
                "id": next_content.id,
                "name": next_content.name,
            } if next_content and is_lecture_accessible(request.user, next_content) else None,
            "contents": SectionPlayerSerializer(sections, many=True, context={"request": request}).data
        }
        return APIResponse.success(data=data)

# 🔹 Mark Progress
class CompleteLectureView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, id=lecture_id)
        progress, _ = LecturesProgress.objects.get_or_create(
            user=request.user, 
            lecture=lecture,
            defaults={'course': lecture.section.course}
        )
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()
        return APIResponse.success(message="Lecture marked as completed.")


class CheckCourseCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        
        # 🔹 Check if all lectures are completed
        total_lectures = Lecture.objects.filter(section__course=course).count()
        completed_count = LecturesProgress.objects.filter(
            user=request.user, 
            course=course, 
            is_completed=True
        ).count()

        if total_lectures > 0 and completed_count >= total_lectures:
            enrollment, _ = Enrollment.objects.get_or_create(user=request.user, course=course)
            
            # If not already completed, mark it and generate certificate
            if not enrollment.is_completed:
                enrollment.is_completed = True
                enrollment.save(update_fields=["is_completed"])
            
            # Ensure certificate exists
            certificate, created = Certificate.objects.get_or_create(
                enrollment=enrollment,
                defaults={'course_title': course.title}
            )
            
            return APIResponse.success(
                message="Course completed! Certificate generated." if created else "Course already completed.",
                data={
                    "certificate_generated": True,
                    "certificate_id": str(certificate.certificate_id),
                    "is_completed": True
                }
            )
        
        return APIResponse.success(
            message="Course not yet completed.",
            data={"certificate_generated": False}
        )

# 🔹 Quiz taking and submission
class StudentQuizView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.prefetch_related("questions__options"), id=quiz_id)
        return APIResponse.success(data={
            "title": quiz.title, "description": quiz.description,
            "time_limit": quiz.time_limit_minutes,
            "questions": StudentQuizQuestionSerializer(quiz.questions.all(), many=True).data
        })
        

class QuizSubmissionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        user_answers = request.data.get("answers", []) # [{"q_id": 1, "o_id": 5}, ...]
        
        correct_count = 0
        total_q = quiz.questions.count()
        
        for ans in user_answers:
            q_id = ans.get("q_id")
            o_id = ans.get("o_id")
            if QuestionOption.objects.filter(id=o_id, question_id=q_id, is_correct=True).exists():
                correct_count += 1
        
        score_pct = (correct_count / total_q) * 100 if total_q > 0 else 0
        
        QuizAttempt.objects.create(
            user=request.user, quiz=quiz, score_percentage=score_pct,
            correct_answers=correct_count, total_questions=total_q,
            course=quiz.section.course if quiz.section else quiz.lecture.section.course
        )

        return APIResponse.success(data={
            "score": score_pct, "passed": score_pct >= quiz.passing_score
        })



class StudentProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        # Auto-create profile if missing to prevent "No Student matches" error
        student, _ = Student.objects.get_or_create(user=request.user)

        serializer = StudentProfileSerializer(
            student,
            context={"request": request}
        )
        return APIResponse.success(
            message="Student profile retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def patch(self, request):
        student, _ = Student.objects.get_or_create(user=request.user)

        serializer = StudentProfileSerializer(
            student,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(
                message="Student profile updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            message="Failed to update student profile.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


# Enroll course list views
class EnrollCourseAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    pagination_class = CustomPagination

    def get(self, request):
        enrollments = Enrollment.objects.filter(user=request.user)

        # Filters
        is_active = request.query_params.get("is_active")
        is_completed = request.query_params.get("is_completed")
        is_started = request.query_params.get("is_started")

        if is_active is not None:
            enrollments = enrollments.filter(is_active=is_active.lower() == "true")

        if is_completed is not None:
            enrollments = enrollments.filter(is_completed=is_completed.lower() == "true")

        if is_started is not None:
            enrollments = enrollments.filter(is_started=is_started.lower() == "true")

        enrollments = enrollments.order_by("-id")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(enrollments, request, view=self)
        serializer = EnrollCourseSerializer(page, many=True, context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
            message="Enrolled courses retrieved successfully."
        )

    
        
        
class ExamAssessmentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    pagination_class = CustomPagination

    def get(self, request):
        enrollments = Enrollment.objects.filter(user=request.user)

        # Filters
        is_active = request.query_params.get("is_active")
        is_completed = request.query_params.get("is_completed")
        is_started = request.query_params.get("is_started")

        if is_active is not None:
            enrollments = enrollments.filter(is_active=is_active.lower() == "true")

        if is_completed is not None:
            enrollments = enrollments.filter(is_completed=is_completed.lower() == "true")

        if is_started is not None:
            enrollments = enrollments.filter(is_started=is_started.lower() == "true")

        enrollments = enrollments.order_by("-id")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(enrollments, request, view=self)
        serializer = ExamAssessmentSerializer(page, many=True, context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
            message="Exam assessment courses retrieved successfully."
        )

    