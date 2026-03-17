from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        
        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("instructor", "Instructor"),
        ("owner", "Owner"),
        ("member", "Member"),
        ("affiliate", "Affiliate"),
        ("admin", "Admin"),
    ]
    
    email     = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="student", db_index=True)
    full_name = models.CharField(max_length=150)
    phone       = models.CharField(max_length=20, blank=True)
    avatar      = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_terms_service = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name        = "User"
        verbose_name_plural = "Users"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_instructor(self):
        return self.role == "instructor"

    @property
    def is_owner(self):
        return self.role == "owner"

    @property
    def is_member(self):
        return self.role == "member"

    @property
    def is_affiliate(self):
        return self.role == "affiliate"

    @property
    def is_admin(self):
        return self.role == "admin" or self.is_superuser
    
    
# For email verification and password reset codes
class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=4)
    expires_at = models.DateTimeField()
    purpose = models.CharField(max_length=20,choices=(("verify", "verify"), ("reset", "reset")))
