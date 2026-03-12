from django.db import models
from users.models import User

# Notification model ----
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications" )
  
    type = models.CharField(max_length=50)  
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    def __str__(self):
        return self.title
    
    
"""
Written by Mahedi Hasan Noyon
"""