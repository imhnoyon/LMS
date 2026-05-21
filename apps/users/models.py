from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid
from cloudinary.models import CloudinaryField

# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        if not name or not name.strip():
            raise ValueError("Name is required.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            name=name.strip(),
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("role", "owner")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email,
            name=name,
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("owner", "Platform Owner"),
        ("Or_admin", "Or_Admin"),
        ("manager", "Manager"),
        ("reviewer", "Reviewer"),
        ("finance", "Finance"),
        ("student", "Student"),
        ("instructor", "Instructor"),
        ("member", "Member"),
        ("affiliate", "Affiliate"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150,blank=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="student", db_index=True)

    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    # avatar=CloudinaryField('avatar', blank=True, null=True)
    signature = models.ImageField(upload_to="signatures/", blank=True, null=True)
    # signature=CloudinaryField('signature', blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    accepted_terms = models.BooleanField(default=False)
    
    platform_revenue= models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]
    def get_biography(self):
        if self.role == "instructor":
            return self.instructor.biography
        return None
    
    def signature_url(self):
        if self.signature:
            return self.signature.url
        return None

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


    @property
    def is_owner(self):
        return self.role == "owner" or self.is_superuser

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_manager(self):
        return self.role == "manager"

    @property
    def is_reviewer(self):
        return self.role == "reviewer"

    @property
    def is_finance(self):
        return self.role == "finance"


class OTP(models.Model):
    PURPOSE_CHOICES = (
        ("verify", "Verify Account"),
        ("reset", "Reset Password"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["purpose"]),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"