from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


# Create your models here.
class Notification(models.Model):
    TYPE_CHOICES = [
        ('payment',    'Payment'),
        ('enrollment', 'Enrollment'),
        ('review',     'Review'),
        ('message',    'Message'),
        ('system',     'System'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=255)
    body       = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ['-created_at']