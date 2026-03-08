from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male'
        FEMALE = 'female'
        OTHER = 'other'

    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    bio = models.TextField(blank=True)
    profile_photo = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'student_profiles'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
