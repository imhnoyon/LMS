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
    
    enrolled_at = models.DateTimeField(auto_now_add=False)

    class Meta:
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user} - {self.course.title}"
    
    
    
    
    
    
"""
Written by Mahedi Hasan Noyon
"""