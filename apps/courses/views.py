from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Q
from utils.helper_functions import parse_duration_to_days
from utils.permissions import IsInstructor, IsOrganization, IsInstructorOrOrganization, IsStudent
from .models import *
from .serializers import *
from utils.api_response import APIResponse
from utils.paginations import CustomPagination
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import json
from apps.organizations.models import Membership

# Helper function to check course ownership or organization access
def get_course_with_permission(course_id, user):
    course = get_object_or_404(Course, pk=course_id)
    
    # Check 1: User is the direct instructor
    if course.instructor == user:
        return course
        
    # Check 2: User is an admin/manager of the course's organization
    if course.organization:
        is_org_admin = Membership.objects.filter(
            organization=course.organization,
            user=user,
            role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER],
            status=Membership.Status.ACTIVE
        ).exists()
        if is_org_admin:
            return course
            
    return None

# Create categories by admin (for now, we can create them via admin panel)
class CategoryAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search')

        categories = Category.objects.all().order_by('-created_at')

        if search:
            categories = categories.filter(
                Q(name__icontains=search) |
                Q(slug__icontains=search)
            )

        serializer = CategorySerializer(
            categories,   
            many=True,
            context={"request": request}
        )

        return APIResponse.success(
            data=serializer.data,
            message="Categories retrieved successfully."
        )
        
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

# ── Step 1: Create course (Basic Info) 
class CourseCreateView(APIView):
    permission_classes = [IsInstructorOrOrganization, IsAuthenticated]
    
    def post(self, request):
        serializer = CourseBasicSerializer(data=request.data)
        if serializer.is_valid():
            organization = None
            # If user is an organization admin, link the course to the organization
            if request.user.role == "Or_admin":
                membership = Membership.objects.filter(
                    user=request.user, 
                    role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER],
                    status=Membership.Status.ACTIVE
                ).first()
                if membership:
                    organization = membership.organization
            
            course = serializer.save(instructor=request.user, organization=organization)
            return APIResponse.success(data={'id': course.id, **serializer.data}, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        serializer = CourseBasicSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class CourseAdvanceInfoManageView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        advance_info = CourseAdvanceInfo.objects.filter(course=course).first()
        data = request.data.copy()

        outcomes = data.get("outcomes")
        requirements = data.get("requirements")

        try:
            if outcomes and isinstance(outcomes, str):
                data["outcomes"] = json.loads(outcomes)
            if requirements and isinstance(requirements, str):
                data["requirements"] = json.loads(requirements)
        except json.JSONDecodeError:
            return APIResponse.error(
                message="Invalid JSON format in outcomes or requirements.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = CourseAdvanceInfoSerializer(
            instance=advance_info,
            data=data,
            context={"request": request}
        )

        if serializer.is_valid():
            if advance_info is None:
                serializer.save(course=course)
            else:
                serializer.save()

            message = (
                "Course advance info created successfully."
                if advance_info is None
                else "Course advance info updated successfully."
            )

            return APIResponse.success(
                message=message,
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        advance_info = CourseAdvanceInfo.objects.filter(course=course).first()

        if not advance_info:
            return APIResponse.error(
                message="Course advance info not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = CourseAdvanceInfoSerializer(
            advance_info,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return APIResponse.success(
                message="Course advance info updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        advance_info = CourseAdvanceInfo.objects.filter(course=course).first()

        if not advance_info:
            return APIResponse.error(
                message="Course advance info not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        CourseOutcome.objects.filter(course=course).delete()
        CourseRequirement.objects.filter(course=course).delete()
        advance_info.delete()

        return APIResponse.success(
            message="Course advance info, outcomes, and requirements deleted successfully.",
            status_code=status.HTTP_200_OK
        )


# ── Step 2: Advance Info 
class CourseAdvanceView(APIView):
    permission_classes = [IsInstructorOrOrganization, IsAuthenticated]
    
    def post(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        serializer = CourseAdvanceInfoSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

# ── Step 3: Sections & Lectures 
class SectionView(APIView):
    permission_classes = [IsInstructorOrOrganization, IsAuthenticated]
    
    def post(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        serializer = SectionSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, section_id):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        section = get_object_or_404(Section, pk=section_id, course=course)
        serializer = SectionSerializer(section, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, section_id):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied or course not found.", status_code=403)
            
        Section.objects.filter(pk=section_id, course=course).delete()
        return APIResponse.success(message="Section deleted successfully.")

#  step -3 lecture added views
class LectureView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, section_id):
        section = get_object_or_404(Section, pk=section_id)
        # Check course permission
        if not get_course_with_permission(section.course.id, request.user):
            return APIResponse.error(message="Access denied.", status_code=403)

        serializer = LectureSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save(section=section)
            return APIResponse.success(
                message="Lecture created successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        return APIResponse.error(
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, section_id, lecture_id):
        lecture = get_object_or_404(Lecture, pk=lecture_id, section_id=section_id)
        if not get_course_with_permission(lecture.section.course.id, request.user):
            return APIResponse.error(message="Access denied.", status_code=403)

        serializer = LectureSerializer(
            lecture,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(
                message="Lecture updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def get(self, request, section_id, lecture_id=None):
        section = get_object_or_404(Section, pk=section_id)
        if lecture_id:
            lecture = get_object_or_404(Lecture, pk=lecture_id, section_id=section_id)
            serializer = LectureSerializer(lecture, context={"request": request})
            return APIResponse.success(
                message="Lecture retrieved successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        lectures = Lecture.objects.filter(section_id=section_id).order_by("order")
        serializer = LectureSerializer(lectures, many=True, context={"request": request})
        return APIResponse.success(
            message="Lecture list retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def delete(self, request, section_id, lecture_id):
        lecture = get_object_or_404(Lecture, pk=lecture_id, section_id=section_id)
        if not get_course_with_permission(lecture.section.course.id, request.user):
            return APIResponse.error(message="Access denied.", status_code=403)
            
        lecture.delete()
        return APIResponse.success(
            message="Lecture deleted successfully.",
            status_code=status.HTTP_200_OK
        )



# ── Quiz 
class QuizView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]
    
    def post(self, request, section_id):
        section = get_object_or_404(Section, pk=section_id)
        if not get_course_with_permission(section.course.id, request.user):
            return APIResponse.error(message="Access denied.", status_code=403)

        serializer = QuizSerializer(data=request.data)
        if serializer.is_valid():
            quiz = serializer.save(section=section)

            question_order = 1
            for q_data in request.data.get('questions', []):
                options = q_data.pop('options', [])
                question = Question.objects.create(
                    quiz=quiz,
                    order=question_order,
                    **q_data
                )
                question_order += 1
                option_order = 1
                for opt in options:
                    QuestionOption.objects.create(
                        question=question,
                        order=option_order,
                        **opt
                    )
                    option_order += 1

            return APIResponse.success(
                data=QuizSerializer(quiz).data,
                status_code=status.HTTP_201_CREATED
            )

        return APIResponse.error(
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

# ── Step 4: Publish 
class PublishCourseView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]
    
    def patch(self, request, pk):
        course = get_course_with_permission(pk, request.user)
        if not course:
            return APIResponse.error(message="Access denied.", status_code=403)
            
        course.status = 'published'
        course.save()
        return APIResponse.success(data={'status': 'published'})
    
    
    
# course list
class CourseListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    paginator_class = CustomPagination

    def get(self, request):
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        status_param = request.query_params.get('status')

        courses = Course.objects.all().order_by('-id')

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search) |
                Q(language__icontains=search) |
                Q(level__icontains=search)
            )

        if category:
            courses = courses.filter(category__name__iexact=category)
        if status_param:
            courses = courses.filter(status__iexact=status_param)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = CourseDetailSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)
    
# Course list Seen by Instructor
class CourseListByInstructorView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]
    paginator_class = CustomPagination

    def get(self, request):
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        status_param = request.query_params.get('status')

        courses = Course.objects.filter(instructor=request.user).order_by('-id')
        

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search) |
                Q(language__icontains=search) |
                Q(level__icontains=search)
            )

        if category:
            courses = courses.filter(category__name__iexact=category)
        if status_param:
            courses = courses.filter(status__iexact=status_param)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = CourseDetailSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)
    
    
    
class courseDetail(APIView):
    def get(self,request,pk):
        course = Course.objects.get(pk=pk)
        serializer = CourseDetailSerializer(course,context={"request": request})
        return APIResponse.success(data=serializer.data)
    
    
    def patch(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        status_value = request.data.get("status")
        if not status_value:
            return APIResponse.error(
                message="Status is required",
                status_code=400
            )
            
        if status_value == "accepted":
            course.status = "accepted"
        elif status_value == "rejected":
            course.status = "rejected"
        course.save()
        
        CourseReviewHistory.objects.create(
            course=course,
            user=request.user,
            status=course.status
        )
        
        return APIResponse.success(
            message="Course status updated successfully",
            data={"status": course.status}
        )
    
    
    

# ── Live Class Management (Instructor) ───────────────────────────────────

class LiveClassManageView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]
    pagination_class = CustomPagination

    def post(self, request, course_id):
        course = get_object_or_404(Course, pk=course_id, instructor=request.user)
        serializer = LiveClassSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course, instructor=request.user)
            return APIResponse.success(
                message="Live class scheduled successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


    

    def get(self, request, course_id):
        course = get_object_or_404(Course, pk=course_id)
        live_classes = LiveClass.objects.filter(course=course).order_by('-scheduled_date', '-scheduled_time')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(live_classes, request)
        serializer = LiveClassSerializer(page, many=True)
        
        return paginator.get_paginated_response(serializer.data)

    def patch(self, request, course_id, class_id):
        live_class = get_object_or_404(LiveClass, id=class_id, course_id=course_id)
        if not get_course_with_permission(course_id, request.user):
            return APIResponse.error(message="Access denied.", status_code=403)
            
        serializer = LiveClassSerializer(live_class, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(
                message="Live class updated successfully.",
                data=serializer.data
            )
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, course_id, class_id):
        live_class = get_object_or_404(LiveClass, id=class_id, course_id=course_id)
        if not get_course_with_permission(course_id, request.user):
            return APIResponse.error(message="Access denied.", status_code=403)
            
        live_class.delete()
        return APIResponse.success(message="Live class deleted successfully.")


# ── Instructor Live Class Stats 
class InstructorLiveClassStatsView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorOrOrganization]

    def get(self, request):
        from django.utils import timezone
        now = timezone.now()
        
        # Stats based on accessible courses (direct instructor or org admin)
        if request.user.role == "Or_admin":
             membership = Membership.objects.filter(
                user=request.user,
                role__in=[Membership.Role.ADMIN, Membership.Role.MANAGER],
                status=Membership.Status.ACTIVE
            ).first()
             if membership:
                 live_classes = LiveClass.objects.filter(course__organization=membership.organization)
             else:
                 live_classes = LiveClass.objects.none()
        else:
            live_classes = LiveClass.objects.filter(instructor=request.user)
        
        total_live_classes = live_classes.count()
        
        upcoming_sessions = live_classes.filter(
            Q(scheduled_date__gt=now.date()) | 
            Q(scheduled_date=now.date(), scheduled_time__gt=now.time())
        ).order_by('scheduled_date', 'scheduled_time')
        
        past_sessions = live_classes.filter(
            Q(scheduled_date__lt=now.date()) | 
            Q(scheduled_date=now.date(), scheduled_time__lte=now.time())
        ).order_by('-scheduled_date', '-scheduled_time')
        
        upcoming_live_classes_count = upcoming_sessions.count()
        
        from apps.enrollments.models import Enrollment
        if request.user.role == "Or_admin":
             students_enrolled = Enrollment.objects.filter(
                course__organization=membership.organization if membership else None, 
                is_active=True
            ).values('user').distinct().count()
        else:
            students_enrolled = Enrollment.objects.filter(
                course__instructor=request.user, 
                is_active=True
            ).values('user').distinct().count()

        upcoming_serialized = LiveClassSerializer(upcoming_sessions, many=True).data
        past_serialized = LiveClassSerializer(past_sessions, many=True).data

        return APIResponse.success(
            data={
                "total_live_classes": total_live_classes,
                "upcoming_live_classes_count": upcoming_live_classes_count,
                "students_enrolled": students_enrolled,
                "upcoming_sessions": upcoming_serialized,
                "past_sessions": past_serialized
            }
        )



class CourseListapiView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    paginator_class = CustomPagination

    def get(self, request):
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        status_param = request.query_params.get('status')

        courses = Course.objects.filter(status='published').order_by('-id')

        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search) |
                Q(language__icontains=search) |
                Q(level__icontains=search)
            )

        if category:
            courses = courses.filter(category__name__iexact=category)
        if status_param:
            courses = courses.filter(status__iexact=status_param)

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = CourseDetailSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)
    
    
    
    
class courseAdminReviewHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get(self, request):
        course_id = request.query_params.get('course_id')
        review_history = CourseReviewHistory.objects.all()

        if course_id:
            review_history = review_history.filter(course_id=course_id)
            
        review_history = review_history.order_by('-reviewed_at')
        
        paginator = self.pagination_class()
        paginated_history = paginator.paginate_queryset(review_history, request)
        serializer = courseReviewHistorySerializer(paginated_history, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    
    
    
    
class CourseHomeListView(APIView):

    def get(self, request):
        from django.db.models import Count, Avg

        # Pre-annotate the average rating via the database since `Course.rating()` is a Python method and cannot be directly sorted/filtered by the ORM
        courses_query = Course.objects.filter(status='accepted').annotate(
            avg_rating=Avg('reviews__rating')
        )

        # 1. Trending Courses (Based on most enrollments, fallback to highest average rating)
        trending = courses_query.annotate(
            enr_count=Count('enrollments')
        ).order_by('-enr_count', '-avg_rating')[:10]

        # 2. Featured Courses (Highly rated courses, or randomize if not enough data)
        featured = courses_query.filter(avg_rating__gte=4.0).order_by('?')[:10]
        if not featured.exists():
            featured = courses_query.order_by('?')[:10]

        # 3. Most Requested Courses (Newest/Latest additions)
        most_requested = courses_query.order_by('-created_at')[:10]
        
        instructors = Instructor.objects.all().select_related('user').distinct()
        instructor_serializer = instructorSerializers(instructors, many=True, context={"request": request})
        # Group data exactly as required by the 3 horizontal UI carousels
        data = {
            "trending_courses": CourseDetailSerializer(trending, many=True, context={"request": request}).data,
            "featured_courses": CourseDetailSerializer(featured, many=True, context={"request": request}).data,
            "most_requested_courses": CourseDetailSerializer(most_requested, many=True, context={"request": request}).data,
            "instructors": instructor_serializer.data
        }

        return APIResponse.success(
            message="Home page courses retrieved successfully.",
            data=data,
            status_code=200
        )
        
        
# Student Courses pages        
class CoursesHomeView(APIView):
    paginator_class = CustomPagination

    def get(self, request):
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        status_param = request.query_params.get('status')
        ratings= request.query_params.get('ratings')
        sort = request.query_params.get("sort")
        
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        
        min_duration = request.query_params.get("min_duration")
        max_duration = request.query_params.get("max_duration")
        

        courses = Course.objects.all().order_by('-id')
        
        if min_price:
            courses = courses.filter(price__gte=min_price)

        if max_price:
            courses = courses.filter(price__lte=max_price)
            
        from django.db.models import Count, Avg

        if sort == "trending":
            courses = courses.annotate(total_enrollments=Count('enrollments')).order_by('-total_enrollments')

        elif sort == "high_rated":
            courses = courses.annotate(average_rating=Avg('reviews__rating')).order_by('-average_rating')  

        elif sort == "newest":
            courses = courses.order_by('-created_at')

        elif sort == "relevance":
            courses = courses.order_by('-id')  

        else:
            courses = courses.order_by('-created_at') 
            
        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(topic__icontains=search) |
                Q(language__icontains=search) |
                Q(level__icontains=search)
            )

        if category:
            courses = courses.filter(category__name__iexact=category)
        if status_param:
            courses = courses.filter(status__iexact=status_param)
            
        if ratings:
            courses = courses.filter(reviews__rating__gte=ratings).distinct()
            
        # Helper function to convert varied textual durations into simple days
        from utils.helper_functions import parse_duration_to_days
        

        if min_duration or max_duration:
            min_d_val = parse_duration_to_days(min_duration) if min_duration else 0
            max_d_val = parse_duration_to_days(max_duration) if max_duration else float('inf')
            
            # Since the db column is textual ("5 weeks"), we logically evaluate and filter the records in memory
            valid_courses = []
            for course in courses:
                course_d_val = parse_duration_to_days(course.duration)
                if min_d_val <= course_d_val <= max_d_val:
                    valid_courses.append(course)
            courses = valid_courses

        paginator = self.paginator_class()
        paginated_courses = paginator.paginate_queryset(courses, request)

        serializer = CourseDetailSerializer(
            paginated_courses,
            many=True,
            context={"request": request}
        )

        return paginator.get_paginated_response(serializer.data)
    
    

class CourseInformationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        courses = Course.objects.all().order_by('-created_at')

        serializer = courseInformationserializer(
            courses,
            many=True,
            context={"request": request}
        )

        return APIResponse.success(
            data= serializer.data,
            message="Course list retrieved successfully"
        )
        
        
        
class CommentLectureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # 🔹 GET: list comments (lecture wise)
    def get(self, request, lecture_id):
        comments = Comment.objects.filter(
            lecture_id=lecture_id,
            parent__isnull=True   # only top-level comments
        ).select_related('user').prefetch_related('replies').order_by('-created_at')

        serializer = CommentLectureSerializer(comments, many=True, context={"request": request})

        return APIResponse.success(
            data={"comments": serializer.data},
            message="Comments retrieved successfully"
        )

    # 🔹 POST: create comment / reply
    def post(self, request):
        user = request.user

        lecture_id = request.data.get("lecture")
        text = request.data.get("text")
        parent_id = request.data.get("parent")

        lecture = get_object_or_404(Lecture, pk=lecture_id)

        comment = Comment.objects.create(
            course=lecture.section.course,
            lecture_id=lecture_id,
            user=user,
            text=text,
            parent_id=parent_id if parent_id else None
        )

        serializer = CommentLectureSerializer(comment, context={"request": request})

        return APIResponse.success(
            data=serializer.data,
            message="Comment added successfully"
        )
        
        
        
        
class MarkLiveClassPresentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        obj = get_object_or_404(LiveClass, id=id)

        LiveClass.objects.update(is_present=False)
        obj.is_present = True
        obj.save()

        return APIResponse.success(
            data={
                "message": "LiveClass marked as present successfully",
                "id": obj.id,
                "is_present": obj.is_present
            }
        )