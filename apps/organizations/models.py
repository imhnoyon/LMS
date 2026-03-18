from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from apps.courses.models import Course
import uuid
from django.utils import timezone


User = get_user_model()


# Create your models here.
class Organization(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE,null=True,blank=True, related_name="organization", limit_choices_to={"role": "owner"})

    # ── Basic Info ────────────────────────────────────
    name     = models.CharField(max_length=255)
    bio      = models.TextField(blank=True,null=True, help_text="Short description about the organization")

    # ── Media — Screen 1, 2, 13 ───────────────────────
    photo  = models.ImageField(upload_to="org/photos/",  blank=True, null=True)
    banner = models.ImageField(upload_to="org/banners/", blank=True, null=True)

    # ── Contact & Social ──────────────────────────────
    phone    = models.CharField(max_length=20, blank=True)
    email    = models.EmailField(blank=True, help_text="Public contact email (different from owner login email)")

    # ── Stats & Ratings ──────────────────────────────
    rating         = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],)
    total_reviews  = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    total_courses  = models.PositiveIntegerField(default=0)

    # ── Status ────────────────────────────────────────
    is_active   = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False, db_index=True, help_text="Verified organizations are highlighted in search results and get a badge on their profile.")
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_organizations")

    # ── Timestamps ────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Organization"
        verbose_name_plural = "Organizations"
        ordering            = ["-created_at"]

    def __str__(self):
        return self.name

    # ── Helpers ───────────────────────────────────────

    def get_active_members(self):
        return self.members.filter(status=Team.Status.ACTIVE)

    def get_active_instructors(self):
        return self.instructors.filter(status=Team.Status.ACTIVE)

    def get_member_count_by_status(self):
        members = self.members.all()
        return {
            "total":     members.count(),
            "active":    members.filter(status="active").count(),
            "suspended": members.filter(status="suspended").count(),
            "admins":    members.filter(role="admin").count(),
        }

    def get_instructor_count_by_status(self):
        instructors = self.instructors.all()
        return {
            "total":         instructors.count(),
            "active":        instructors.filter(status="active").count(),
            "pending":       instructors.filter(status="pending").count(),
            "total_courses": self.courses.filter(status="published").count(),
        }


# ─────────────────────────────────────────
# Team Management
# ─────────────────────────────────────────
class Team(models.Model):
    class Role(models.TextChoices):
        ADMIN    = "admin",    "Admin"
        MANAGER  = "manager",  "Manager"
        TRAINER  = "trainer",  "Trainer"
        FINANCE  = "finance",  "Finance"
        REVIEWER = "reviewer", "Reviewer"

    class Status(models.TextChoices):
        ACTIVE    = "active",    "Active"
        INVITED   = "invited",   "Invited"
        SUSPENDED = "suspended", "Suspended"
        REMOVED   = "removed",   "Removed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role       = models.CharField(max_length=30, choices=Role.choices, default=Role.TRAINER)
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_member_invitations")
    last_login = models.DateTimeField(null=True, blank=True)
    joined_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together     = ("organization", "user")
        verbose_name        = "Team"
        verbose_name_plural = "Teams"
        ordering            = ["role", "-joined_at"]

    def __str__(self):
        return f"{self.user.email} — {self.role} @ {self.organization.name}"


# ─────────────────────────────────────────
# Role Permission
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# Contract
# ─────────────────────────────────────────

class Contract(models.Model):

    class Status(models.TextChoices):
        ONGOING   = "ongoing",   "Ongoing"
        EXPIRED   = "expired",   "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization  = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="contracts")
    instructor = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="contracts")
    course = models.ForeignKey(Course, on_delete=models.CASCADE,related_name="contracts")
    revenue_share = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
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
        if self.expiry_date < timezone.now().date():
            self.status = self.Status.EXPIRED
        super().save(*args, **kwargs)


# ─────────────────────────────────────────
# Member Invitation
# ─────────────────────────────────────────

class MemberInvitation(models.Model):

    class InviteType(models.TextChoices):
        TEAM_MEMBER = "team_member", "Team Member"
        INSTRUCTOR  = "instructor",  "Instructor"

    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED  = "expired",  "Expired"
        REVOKED  = "revoked",  "Revoked"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(User,on_delete=models.CASCADE, related_name="sent_invitations")
    email       = models.EmailField()
    invite_type = models.CharField(max_length=20, choices=InviteType.choices)
    token      = models.UUIDField(default=uuid.uuid4, unique=True)
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("organization", "email", "invite_type")

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite → {self.email} as {self.invite_type} @ {self.organization.name}"

