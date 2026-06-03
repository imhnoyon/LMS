from django.contrib.auth import get_user_model
from apps.courses.models import Course
from django.db import models
import uuid

User = get_user_model()

# Create your models here.
# ══════════════════════════════════════════════════════════════════
# HUMAN CHAT
# ══════════════════════════════════════════════════════════════════ 
class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation #{self.pk}"

    def get_other_participant(self, current_user):
        return self.participants.exclude(id=current_user.id).first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    STATUS_CHOICES = [
        ('sent',      'Sent'),
        ('delivered', 'Delivered'),
        ('read',      'Read'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body         = models.TextField()
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} → #{self.conversation_id} | {self.body[:40]}"


# ══════════════════════════════════════════════════════════════════
# AI ASSISTANT
# ══════════════════════════════════════════════════════════════════
class Session(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    course     = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.session_id} — {self.user}"


class Chat(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('ai',   'AI Tutor'),
    ]

    session    = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    sender     = models.CharField(max_length=5, choices=SENDER_CHOICES)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender}] {self.body[:60]}"