from django.utils import timezone
import uuid
from django.db import models
from apps.users.models import User
from apps.courses.models import Course
from apps.orders.models import Order


# Student Enrollment model ----  
class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    is_active = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False) # When student completes the course, we will mark this as True
    is_started = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(auto_now_add=False)

    class Meta:
        unique_together = ["user", "course"]

    def save(self, *args, **kwargs):
        # 🔹 Handle Certificate Generation
        if self.is_completed:
            # Check if certificate already exists to avoid duplication
            if not hasattr(self, 'certificate'):
                super().save(*args, **kwargs) # Save enrollment first
                Certificate.objects.get_or_create(
                    enrollment=self,
                    defaults={'course_title': self.course.title}
                )
                return
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.name} - {self.course.title} ({'Completed' if self.is_completed else 'Active'})"
    
    
# if we want to generate certificates for students who complete the course, we can create a Certificate model like this ----   
from django.db import models, transaction
def generate_certificate_id():
    with transaction.atomic():
        last = Certificate.objects.select_for_update().order_by('-id').first()

        if last and last.certificate_id:
            last_number = int(last.certificate_id.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"Learn-Hub-{str(new_number).zfill(4)}"
    
class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment,on_delete=models.CASCADE,related_name="certificate")
    
    course_title = models.CharField(max_length=255)
    certificate_id = models.CharField(max_length=50, unique=True, blank=True)
    issue_date = models.DateField(auto_now_add=True)
    
    def student_name(self):
        return self.enrollment.user.name
    
    class Meta:
        ordering = ["-issue_date"]
        
        
    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = generate_certificate_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.enrollment.user.name} - {self.enrollment.course.title}"
    
    
"""
Written by Mahedi Hasan Noyon
"""