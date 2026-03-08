from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


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


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        ADMIN = 'admin'
        INSTRUCTOR = 'instructor'
        STUDENT = 'student'

    class Status(models.TextChoices):
        ACTIVE = 'active'
        INACTIVE = 'inactive'
        SUSPENDED = 'suspended'

    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    last_active = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
