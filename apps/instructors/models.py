from django.conf import settings
from django.db import models
from apps.organizations.models import Organization


class InstructorProfile(models.Model):
    class InstructorType(models.TextChoices):
        ORGANIZATION = 'organization'
        FREELANCER = 'freelancer'

    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='instructor_profile',)
    bio = models.TextField(blank=True)
    expertise = models.CharField(max_length=255, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='instructor_photos/', blank=True, null=True)
    
    instructor_type = models.CharField(max_length=20,choices=InstructorType.choices,default=InstructorType.FREELANCER)
    organization = models.ForeignKey(Organization,on_delete=models.SET_NULL,null=True,blank=True,related_name='instructors')

    class Meta:
        db_table = 'instructor_profiles'
