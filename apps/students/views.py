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
from django.db.models import Q

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
            enrollment.course for enrollment in enrollments.order_by("-enrolled_at")[:6]
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
                "attachment_file": request.build_absolute_uri(current_lecture.LectureAttachment.url) if current_lecture.LectureAttachment else None,
                "lecture_notes": current_lecture.lecture_notes,
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
        is_completed = QuizAttempt.objects.filter(user=request.user, quiz=quiz).exists()
        return APIResponse.success(data={
            "title": quiz.title, "description": quiz.description,
            "time_limit": quiz.time_limit_minutes,
            "questions": StudentQuizQuestionSerializer(quiz.questions.all(), many=True).data,
            "is_completed": is_completed
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

        wrong_count = max(total_q - correct_count, 0)
        score_pct = round(score_pct, 2)

        return APIResponse.success(data={
            "quiz_id": quiz.id,
            "quiz_title": quiz.title,
            "score": score_pct,
            "completion_percentage": score_pct,
            "total_questions": total_q,
            "correct_answers": correct_count,
            "wrong_answers": wrong_count,
            "passed": score_pct >= quiz.passing_score,
            "is_completed": True
        })



class StudentProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
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
        course_title = request.query_params.get("course_title")
        is_active = request.query_params.get("is_active")
        is_completed = request.query_params.get("is_completed")
        is_started = request.query_params.get("is_started")

        if course_title:
            enrollments = enrollments.filter(course__title__icontains=course_title)

        if is_active is not None:
            enrollments = enrollments.filter(is_active=is_active.lower() == "true")

        if is_completed is not None:
            enrollments = enrollments.filter(is_completed=is_completed.lower() == "true")

        if is_started is not None:
            enrollments = enrollments.filter(is_started=is_started.lower() == "true")

        course_ids = enrollments.values_list("course_id", flat=True)

        total_lectures_all_courses = Lecture.objects.filter(
            section__course_id__in=course_ids
        ).count()
        completed_lectures_all_courses = LecturesProgress.objects.filter(
            user=request.user,
            is_completed=True,
            lecture__section__course_id__in=course_ids
        ).count()

        average_completion_percentage = 0.0
        if total_lectures_all_courses > 0:
            average_completion_percentage = round(
                (completed_lectures_all_courses / total_lectures_all_courses) * 100,
                2
            )

        total_completed_courses = enrollments.filter(is_completed=True).count()
        total_certificated_courses = Certificate.objects.filter(
            enrollment__user=request.user,
            enrollment__course_id__in=course_ids,
        ).count()

        completed_quiz_ids = set()
        quiz_attempts = QuizAttempt.objects.filter(
            user=request.user,
            course_id__in=course_ids,
        ).select_related("quiz").order_by("quiz_id", "-submitted_at")

        seen_quiz_ids = set()
        for attempt in quiz_attempts:
            if attempt.quiz_id in seen_quiz_ids:
                continue
            seen_quiz_ids.add(attempt.quiz_id)
            if attempt.score_percentage >= attempt.quiz.passing_score:
                completed_quiz_ids.add(attempt.quiz_id)

        enrollments = enrollments.order_by("-id")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(enrollments, request, view=self)
        serializer = ExamAssessmentSerializer(page, many=True, context={"request": request})

        response = paginator.get_paginated_response(
            serializer.data,
            message="Exam assessment courses retrieved successfully."
        )
        response.data["average_completion_percentage"] = average_completion_percentage
        response.data["total_completed_courses"] = total_completed_courses
        response.data["total_certificated_courses"] = total_certificated_courses
        response.data["total_completed_quizzes"] = len(completed_quiz_ids)
        return response



class CourseLectureTrackingProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        course_name = request.query_params.get("course_name")

        progress_qs = LecturesProgress.objects.filter(user=user)\
            .select_related('lecture', 'lecture__section__course')\
            .order_by('-id')[:10]  # Limit to first 10 results

        #  course name filter
        if course_name:
            progress_qs = progress_qs.filter(
                lecture__section__course__title__icontains=course_name
            )

        serializer = coursemodelserializer(
            progress_qs,
            many=True,
            context={"request": request}
        )

        return APIResponse.success(
            data=serializer.data,
            message="Course progress retrieved successfully"
        )
    
# Course Review APIView
class CreateReviewView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

        if not Enrollment.objects.filter(course=course,user=request.user,is_active=True).exists():
            return APIResponse.error(
                message="You must enroll in this course to submit a review.",
                status_code=403
            )
        if Review.objects.filter(course=course, user=request.user).exists():
            return APIResponse.error(
                message="You have already reviewed this course.",
                status_code=400
            )
            
        

        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course, user=request.user)

            return APIResponse.success(
                message="Review submitted successfully.",
                data=serializer.data,
                status_code=201
            )

        return APIResponse.error(
            message="Validation failed.",
            errors=serializer.errors,
            status_code=400
        )
        
    def patch(self, request, review_id):
        review = get_object_or_404(Review, id=review_id)

        if review.user != request.user:
            return APIResponse.error(
                message="You are not allowed to update this review.",
                status_code=403
            )

        serializer = ReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return APIResponse.success(
                message="Review updated successfully.",
                data=serializer.data,
                status_code=200
            )

        return APIResponse.error(
            message="Validation failed.",
            errors=serializer.errors,
            status_code=400
        )
        
        
    
    
class CourseReviewDeleted(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    def delete(self, request, review_id):
        review = get_object_or_404(Review, id=review_id)
        if review.user != request.user:
            return APIResponse.error(
                message="You are not allowed to delete this review.",
                status_code=403
            )
        review.delete()
        return APIResponse.success(
            message="Review deleted successfully.",
            status_code=200
        )
        
        
 # Review List       
class ReviewListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    paginator_class = CustomPagination

    def get(self, request):
        reviews = Review.objects.filter(user=request.user).order_by('-created_at')

        paginator = self.paginator_class()
        page = paginator.paginate_queryset(reviews, request, view=self)
        serializer = ReviewListSerializer(page, many=True, context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
            message="Reviews retrieved successfully."
        )
        
        
# Course Quiz Attempt list      
class CourseQuizAttemptListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination

    def get(self, request):
        attempts = QuizAttempt.objects.filter(
            user=request.user
        ).select_related(
            "user",
            "course",
            "quiz",
        ).order_by("-submitted_at")

        paginator = self.paginator_class()
        page = paginator.paginate_queryset(attempts, request, view=self)
        serializer = CourseQuizAttemptSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(
            serializer.data,
            message="Quiz attempts retrieved successfully."
        )      
        
        
         
# Course Purchase History      
class CoursePurchaseHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination

    def get(self, request):
        enrollments = Enrollment.objects.filter(
            user=request.user
        ).select_related(
            "course",
            "course__instructor",
            "course__advance_info"
        ).order_by("-enrolled_at")

        paginator = self.paginator_class()
        page = paginator.paginate_queryset(enrollments, request, view=self)

        serializer = CoursePurchasesHistory(
            page,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(
            serializer.data,
            message="Course purchase history retrieved successfully."
        )
    

# Change Password api
class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    def patch(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=400
            )

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return APIResponse.error(
                message="Old password is incorrect.",
                status_code=400
            )

        if old_password == new_password:
            return APIResponse.error(
                message="New password must be different from old password.",
                status_code=400
            )

        user.set_password(new_password)
        user.save()

        return APIResponse.success(
            message="Password changed successfully.",
            status_code=200
        )
        
        
# Delete Account
class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated,IsStudent]

    def delete(self, request):
        serializer = DeleteAccountSerializer(data=request.data)

        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=400
            )
        user = request.user
        password = serializer.validated_data["password"]
        if not user.check_password(password):
            return APIResponse.error(
                message="Password is incorrect.",
                status_code=400
            )
            
        from django.utils import timezone

        user.is_active = False
        user.save()
        
        # user.delete()
        return APIResponse.success(
            message="Account deleted successfully.",
            status_code=200
        )
        
        
# Live course
class StudentLiveClassListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        today = timezone.localdate()
        now_time = timezone.localtime().time()

        enrolled_course_ids = Enrollment.objects.filter(
            user=request.user,
            is_active=True
        ).values_list("course_id", flat=True)

        base_queryset = LiveClass.objects.filter(
            course_id__in=enrolled_course_ids
        ).select_related("instructor", "course")

        upcoming_live_classes = base_queryset.filter(
            Q(scheduled_date__gt=today) |
            Q(scheduled_date=today, scheduled_time__gte=now_time)
        ).order_by("scheduled_date", "scheduled_time")

        past_live_classes = base_queryset.filter(
            Q(scheduled_date__lt=today) |
            Q(scheduled_date=today, scheduled_time__lt=now_time)
        ).order_by("-scheduled_date", "-scheduled_time")

        upcoming_serializer = LiveClassStudentSerializer(upcoming_live_classes, many=True, context={"request": request})
        past_serializer = LiveClassStudentSerializer(past_live_classes, many=True, context={"request": request})

        return APIResponse.success(
            message="Live classes fetched successfully.",
            data={
                "upcoming_live_classes": upcoming_serializer.data,
                "past_live_classes": past_serializer.data,
            },
            status_code=status.HTTP_200_OK
        )
        
        
        
        
        
#join live classes 
class JoinLiveClassView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, live_class_id):
        live_class = get_object_or_404(LiveClass, pk=live_class_id)

        # enrollment check
        is_enrolled = Enrollment.objects.filter(
            user=request.user,
            course=live_class.course,
            is_active=True
        ).exists()

        if not is_enrolled:
            return APIResponse.error(
                message="You are not enrolled in this course.",
                status_code=403
            )

        attendance, created = LiveClassAttendance.objects.get_or_create(
            live_class=live_class,
            student=request.user,
            defaults={
                "status": "attended",
                "joined_at": timezone.now()
            }
        )

        if not created:
            attendance.status = "attended"
            attendance.joined_at = timezone.now()
            attendance.save()

        return APIResponse.success(
            message="Joined live class successfully.",
            data={
                "class_link": live_class.class_link
            }
        )
        
        
class StudentPurchasedCourseRecordingListView(APIView):
    permission_classes = [IsAuthenticated]
    paginator_class = CustomPagination
    def get(self, request):
        user = request.user

        if user.role != "student":
            return APIResponse.error(
                message="Only students can access purchased course recordings.",
                status_code=403
            )

        enrolled_course_ids = Enrollment.objects.filter( user=user, is_active=True).values_list("course_id", flat=True)
        recordings = sessionRecordUploader.objects.select_related("course").filter(course_id__in=enrolled_course_ids).order_by("-uploaded_at")
        
        search = request.query_params.get("search")
        if search:
            recordings = recordings.filter(title__icontains=search)
            
        paginator = self.paginator_class()
        page = paginator.paginate_queryset(recordings, request, view=self)
        
        serializer = LiveRecordingVideo(page, many=True,context={"request": request})

        return  paginator.get_paginated_response(
            data=serializer.data,
            message="Purchased course recordings fetched successfully.",
        )
        
    
    

class StudentRecordingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user

        if user.role != "student":
            return APIResponse.error(
                message="Only students can access recording details.",
                status_code=403
            )

        recording = get_object_or_404(
            sessionRecordUploader.objects.select_related("course"),
            pk=pk
        )

        is_enrolled = Enrollment.objects.filter(
            user=user,
            course=recording.course,
            is_active=True
        ).exists()

        if not is_enrolled:
            return APIResponse.error(
                message="You do not have access to this recording.",
                status_code=403
            )

        serializer = LiveRecordingVideo(
            recording,
            context={"request": request}
        )

        return APIResponse.success(
            message="Recording fetched successfully.",
            data=serializer.data,
            status_code=200
        )

# 🔹 My Certificates List View
class StudentCertificateListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    pagination_class = CustomPagination

    def get(self, request):
        certificates = Certificate.objects.filter(
            enrollment__user=request.user,
            enrollment__is_completed=True
        ).order_by('-issue_date')

        paginator = self.pagination_class()
        paginated_certificates = paginator.paginate_queryset(certificates, request, view=self)

        serializer = StudentCertificateSerializer(
            paginated_certificates, many=True, context={'request': request}
        )

        return paginator.get_paginated_response(
            data=serializer.data,
            message="Certificates retrieved successfully."
        )