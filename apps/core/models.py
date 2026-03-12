from django.db import models


# Create your models here.
class Ticket(models.Model):
    STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    
class FAQCategory(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, related_name='faqs', on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question
    
    
class PlatformConfiguration(models.Model):
    CURRENCY_CHOICES = (
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('JPY', 'Japanese Yen'),
        ('INR', 'Indian Rupee'),
    )
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('zh', 'Chinese'),
    )
    name = models.CharField(max_length=255, unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    language = models.CharField(max_length=50, default='en', choices=LANGUAGE_CHOICES)
    currency = models.CharField(max_length=10, default='USD', choices=CURRENCY_CHOICES)
    phone_numbers = models.JSONField(default=list, blank=True)
    email_addresses = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
