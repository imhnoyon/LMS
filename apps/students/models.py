from django.db import models
from django.conf import settings
from datetime import date
import random
import string
import uuid


# Create your models here.
def generate_student_id():
    max_attempts = 10
    for _ in range(max_attempts):
        new_id = 'STU-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Student.objects.filter(id=new_id).exists():
            return new_id
    return 'STU-' + str(uuid.uuid4()).upper().replace('-', '')[:6]


class Student(models.Model):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_student_id,
        editable=False,
        unique=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student",
        limit_choices_to={"role": "student"},
    )
    
    title = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.id} - {self.user.email}"

    @property
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        return None


    def __str__(self):
        return self.user.name
