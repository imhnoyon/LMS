from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from utils.api_response import APIResponse
from apps.courses.models import (
    Course, Section, Lecture, LecturesProgress, 
    Quiz, QuizAttempt, Question, QuestionOption
)
from apps.payments.models import Invoice
from apps.enrollments.models import Enrollment
from .serializers import (
    StudentDashboardSerializer, SectionPlayerSerializer, StudentQuizQuestionSerializer
)
from .helper_funtion import is_lecture_accessible, get_next_lecture, is_quiz_passed

# 🔹 Dashboard Summary
class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        enrollments = Enrollment.objects.filter(user=user)

        enrolled_courses_count = enrollments.count()
        active_courses_count = enrollments.filter(is_active=True, is_completed=False).count()
        completed_courses_count = enrollments.filter(is_completed=True).count()
        recently_enrolled = [
            enrollment.course for enrollment in enrollments.order_by("-enrolled_at")[:4]
        ]

        recent_invoices = Invoice.objects.filter(user=user).order_by("-invoice_date", "-created_at")[:10]

        data = {
            "enrolled_courses_count": enrolled_courses_count,
            "active_courses_count": active_courses_count,
            "completed_courses_count": completed_courses_count,
            "recently_enrolled": recently_enrolled,
            "recent_invoices": recent_invoices,
        }

        serializer = StudentDashboardSerializer(instance=data, context={"request": request})

        return APIResponse.success(
            message="Student dashboard data fetched successfully.",
            data=serializer.data,
            status_code=200
        )


# 🔹 Course Player (Udemy Clone)
class CoursePlayerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, lecture_id=None):
        course = get_object_or_404(Course, id=course_id)
        
        # Check if student is actually enrolled
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return APIResponse.error(message="You are not enrolled in this course.", status_code=403)

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
        progress, _ = LecturesProgress.objects.get_or_create(user=request.user, lecture=lecture)
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()

        # Unlock next logic is handled by 'is_lecture_accessible' in subsequent player calls
        return APIResponse.success(message="Lecture marked as completed.")

# 🔹 Quiz taking and submission
class StudentQuizView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.prefetch_related("questions__options"), id=quiz_id)
        # Security: can only take if section lectures are done
        # (Handling is done in sidebar via is_unlocked)
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
