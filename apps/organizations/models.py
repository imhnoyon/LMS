from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from apps.courses.models import Course
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Q
from datetime import timedelta
from django.db import models
import uuid


User = get_user_model()


def default_expiry():
    return timezone.now() + timedelta(days=7)


# Create your models here.
class Organization(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True, help_text="Short description about the organization")
    photo = models.ImageField(upload_to="org/photos/", blank=True, null=True)
    banner = models.ImageField(upload_to="org/banners/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    # email = models.EmailField(blank=True, help_text="Public contact email")
    

    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_reviews = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    total_courses = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False, db_index=True, help_text="Verified organizations get priority")

    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_organizations")

    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    total_withdrawals = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)

    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_onboarding_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_verified"])]

    def __str__(self):
        return self.name

    def get_active_members(self):
        return self.memberships.filter(status=Membership.Status.ACTIVE)

    def get_active_instructors(self):
        return self.memberships.filter(role=Membership.Role.INSTRUCTOR, status=Membership.Status.ACTIVE)

    def get_member_count_by_status(self):
        members = self.memberships.all()
        return {
            "total": members.count(),
            "active": members.filter(status=Membership.Status.ACTIVE).count(),
            "suspended": members.filter(status=Membership.Status.SUSPENDED).count(),
            "admins": members.filter(role=Membership.Role.ADMIN).count(),
        }

    def get_instructor_count_by_status(self):
        instructors = self.memberships.filter(role=Membership.Role.INSTRUCTOR)
        return {
            "total": instructors.count(),
            "active": instructors.filter(status=Membership.Status.ACTIVE).count(),
        }

    @property
    def owner(self):
        return self.memberships.filter(role=Membership.Role.ADMIN).order_by("joined_at").first()


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        INSTRUCTOR = "instructor", "Instructor"
        FINANCE = "finance", "Finance"
        REVIEWER = "reviewer", "Reviewer"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organization_memberships")

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.INSTRUCTOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_org_user")
        ]
        ordering = ["role", "-joined_at"]
        indexes = [models.Index(fields=["organization", "user"])]

    def __str__(self):
        return f"{self.user.email} — {self.role} @ {self.organization.name}"


class RolePermission(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="role_permissions")
    role_name    = models.CharField(max_length=50)
    permissions  = models.JSONField(
        default=dict,
        help_text="""
        {
            'can_create_course':      true/false,
            'can_edit_course':        true/false,
            'can_delete_course':      true/false,
            'can_view_earnings':      true/false,
            'can_manage_team':        true/false,
            'can_manage_contracts':   true/false,
            'can_manage_instructors': true/false,
            'can_white_label':        true/false
        }
        """,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "role_name")

    def __str__(self):
        return f"{self.organization.name} — {self.role_name} permissions"


class Contract(models.Model):
    class Status(models.TextChoices):
        ONGOING   = "ongoing",   "Ongoing"
        EXPIRED   = "expired",   "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization  = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="contracts")
    instructor = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="contracts")
    course = models.ForeignKey(Course, on_delete=models.CASCADE,related_name="contracts")
    revenue_share = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    expiry_date = models.DateField()
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ONGOING)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Contract"
        verbose_name_plural = "Contracts"
        ordering            = ["-created_at"]

    def __str__(self):
        return (
            f"{self.instructor.user.email} — "
            f"{self.course.title} — "
            f"{int(self.revenue_share * 100)}%"
        )

    def save(self, *args, **kwargs):
        if isinstance(self.expiry_date, str):
            self.expiry_date = parse_date(self.expiry_date)

        if self.expiry_date and self.expiry_date < timezone.now().date():
            self.status = self.Status.EXPIRED
        else:
            self.status = self.Status.ONGOING
        super().save(*args, **kwargs)


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invitations")

    email = models.EmailField()
    role = models.CharField(max_length=30, choices=Membership.Role.choices, default=Membership.Role.INSTRUCTOR)

    token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                condition=Q(status="pending"),
                name="unique_pending_invitation"
            )
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite → {self.email} @ {self.organization.name}"







        