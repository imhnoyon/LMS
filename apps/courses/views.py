from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,IsAdminUser

from utils.permissions import IsInstructor, IsOrganization,IsInstructorOrOrganization
from .models import *
from .serializers import *
from utils.api_response import APIResponse
from utils.paginations import CustomPagination

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


# ── Step 2: Advance Info 
class CourseAdvanceView(APIView):
    def post(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = CourseAdvanceInfoSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)



# ── Outcomes (add/delete) 
class OutcomeView(APIView):
    def post(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = CourseOutcomeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, outcome_id):
        CourseOutcome.objects.filter(pk=outcome_id, course_id=pk).delete()
        return APIResponse.success(message="Outcome deleted successfully.")

# ── Requirements (add/delete) 
class RequirementView(APIView):
    def post(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = CourseRequirementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, req_id):
        CourseRequirement.objects.filter(pk=req_id, course_id=pk).delete()
        return APIResponse.success(message="Requirement deleted successfully.")

# ── Step 3: Sections & Lectures 
class SectionView(APIView):
    def post(self, request, pk):
        course = Course.objects.get(pk=pk, instructor=request.user)
        serializer = SectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course)
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, section_id):
        section = Section.objects.get(pk=section_id, course_id=pk)
        serializer = SectionSerializer(section, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, section_id):
        Section.objects.filter(pk=section_id, course_id=pk).delete()
        return APIResponse.success(message="Section deleted successfully.")

class LectureView(APIView):
    def post(self, request, section_id):
        section = Section.objects.get(pk=section_id)
        serializer = LectureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(section=section)
            return APIResponse.success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, section_id, lecture_id):
        lecture = Lecture.objects.get(pk=lecture_id, section_id=section_id)
        serializer = LectureSerializer(lecture, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(data=serializer.data)
        return APIResponse.error(errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

# ── Lecture Video Upload 
class LectureVideoView(APIView):
    def post(self, request, lecture_id):
        lecture = Lecture.objects.get(pk=lecture_id)
        video, _ = LectureVideo.objects.get_or_create(lecture=lecture)
        video.video_file = request.FILES['video_file']
        video.save()
        return APIResponse.success(data={'message': 'uploaded'}, status_code=status.HTTP_201_CREATED)

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