from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()



class Notification(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=20)
    title      = models.CharField(max_length=255)
    body       = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ['-created_at']