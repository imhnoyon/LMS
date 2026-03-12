from time import timezone
import uuid

from django.db import models
from users.models import User
from courses.models import Course
from orders.models import Order


# Student Enrollment model ----  
class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False) # When student completes the course, we will mark this as True
    enrolled_at = models.DateTimeField(auto_now_add=False)

    class Meta:
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user} - {self.course.title}"
    
    
# if we want to generate certificates for students who complete the course, we can create a Certificate model like this ----   
class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment,on_delete=models.CASCADE,related_name="certificate")
    
    course_title = models.CharField(max_length=255)
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    issue_date = models.DateField(default=timezone.now)
    
    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.enrollment.course.title}"
    
    
"""
Written by Mahedi Hasan Noyon
"""