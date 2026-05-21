from django.db import models
from django.conf import settings
import random
import string
import uuid
from cloudinary.models import CloudinaryField

# Create your models here.
def generate_instructor_id():
    max_attempts = 10
    for _ in range(max_attempts):
        new_id = 'INS-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Instructor.objects.filter(id=new_id).exists():
            return new_id
    return 'INS-' + str(uuid.uuid4()).upper().replace('-', '')[:6]


class Instructor(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_instructor_id,
        editable=False,
        unique=True
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor"
    )
    title = models.CharField(max_length=100, blank=True, null=True)
    biography = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    total_withdrawals = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    signature = models.ImageField(upload_to="signatures/", blank=True, null=True)
    # signature=CloudinaryField('signature', blank=True, null=True)
    is_organization_instructor = models.BooleanField(default=False)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "instructors"
        ordering = ["-created_at"]
        
    @property
    def courses(self):
        """Access courses through the related user"""
        return self.user.courses.all()

    def Instructor_name(self):
        if self.user.name:
            return f"{self.user.name}"
        return self.user.email

    def __str__(self):
        return f"{self.id} - {self.user.email}"
