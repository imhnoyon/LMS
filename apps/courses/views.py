from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from django.db.models import Q
from utils.permissions import IsInstructor, IsOrganization,IsInstructorOrOrganization
from .models import *
from .serializers import *
from utils.api_response import APIResponse
from utils.paginations import CustomPagination
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import json

# Create categories by admin (for now, we can create them via admin panel)
class CategoryAPIView(APIView):
    permission_classes = [IsAdminUser, IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        categories = Category.objects.all().order_by('-created_at')
        paginator = self.pagination_class()
        paginated_categories = paginator.paginate_queryset(categories, request, view=self)
        serializer = CategorySerializer(paginated_categories,many=True,context={"request": request})

        return paginator.get_paginated_response(
            serializer.data,
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
            course = serializer.save(instructor=request.user)
            return APIResponse.success(data={'id': course.id, **serializer.data}, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = CourseBasicSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class CourseAdvanceInfoManageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk, instructor=request.user)
        advance_info = CourseAdvanceInfo.objects.filter(course=course).first()

        data = request.data.copy()

        outcomes = data.get("outcomes")
        requirements = data.get("requirements")

        # Parse JSON only if they are strings (typical for multipart/form-data)
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
            # If creating a new AdvanceInfo, pass the course.
            # If updating, the course is already on the instance.
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
        course = get_object_or_404(Course, pk=pk, instructor=request.user)
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
        course = get_object_or_404(Course, pk=pk, instructor=request.user)
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
    def post(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = CourseAdvanceInfoSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)




# ── Step 3: Sections & Lectures 
class SectionView(APIView):
    def post(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = SectionSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, section_id):
        section = Section.objects.get(pk=section_id, course_id=pk)
        serializer = SectionSerializer(section, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, section_id):
        Section.objects.filter(pk=section_id, course_id=pk).delete()
        return APIResponse.success(message="Section deleted successfully.")

#  step -3 lecture added views
class LectureView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, section_id):
        section = get_object_or_404(Section, pk=section_id)

        data = request.data.copy()

        data['video_file'] = request.FILES.get('video_file')
        data['LectureAttachment'] = request.FILES.get('LectureAttachment')
        data['LectureNoteFile'] = request.FILES.get('LectureNoteFile')
        
        serializer = LectureSerializer(data=data, context={"request": request})
        
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
        lecture.delete()
        return APIResponse.success(
            message="Lecture deleted successfully.",
            status_code=status.HTTP_200_OK
        )



# ── Quiz 
class QuizView(APIView):
    def post(self, request, section_id):
        section = Section.objects.get(pk=section_id)
        serializer = QuizSerializer(data=request.data)
        if serializer.is_valid():
            quiz = serializer.save(section=section)
            # Save questions + options
            for q_data in request.data.get('questions', []):
                options = q_data.pop('options', [])
                question = Question.objects.create(quiz=quiz, **q_data)
                for opt in options:
                    QuestionOption.objects.create(question=question, **opt)
            return APIResponse.success(data=QuizSerializer(quiz).data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

# ── Step 4: Publish 
class PublishCourseView(APIView):
    def patch(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
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
            courses = courses.filter(category_id=category)

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
        course.status = status_value
        course.save()
        return APIResponse.success(
            message="Course status updated successfully",
            data={"status": course.status}
        )
    
    
    

