from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        return self.create_user(email, username, password, **extra_fields)


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
    username    = models.CharField(max_length=150, unique=True)
    phone       = models.CharField(max_length=20, blank=True)
    avatar      = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username"]

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
    
    
    
