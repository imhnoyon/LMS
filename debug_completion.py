import os
import django
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.courses.models import Course, Lecture, LecturesProgress
from apps.users.models import User

# Get the last active student
user = User.objects.filter(role='student').first()
course = Course.objects.get(id=9)

total_lectures = Lecture.objects.filter(section__course=course).count()
completed_count = LecturesProgress.objects.filter(
    user=user, 
    course=course, 
    is_completed=True
).count()

print(f"User: {user.email}")
print(f"Course: {course.title}")
print(f"Total Lectures: {total_lectures}")
print(f"Completed Lectures: {completed_count}")

# List lectures
for lecture in Lecture.objects.filter(section__course=course):
    progress = LecturesProgress.objects.filter(user=user, lecture=lecture).first()
    print(f"- {lecture.name}: {'Completed' if progress and progress.is_completed else 'NOT completed'}")

if total_lectures > 0 and completed_count >= total_lectures:
    print("LOGIC SAYS COMPLETED")
else:
    print("LOGIC SAYS NOT COMPLETED")
