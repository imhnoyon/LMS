from django.db import models
from django.conf import settings
import random
import string
import uuid


# Create your models here.
def generate_contact_id():
    max_attempts = 10
    for _ in range(max_attempts):
        new_id = 'CON-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Contact.objects.filter(id=new_id).exists():
            return new_id
    return 'CON-' + str(uuid.uuid4()).upper().replace('-', '')[:6]


class Contact(models.Model):
    STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('spam', 'Spam'),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=10,
        editable=False,
        default=generate_contact_id,
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["email"]),
        ]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"

    def __str__(self):
        return f"{self.name} — {self.subject}"
    
    
class FAQCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "FAQ Category"
        verbose_name_plural = "FAQ Categories"

    def __str__(self):
        return self.name


class FAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(FAQCategory, related_name='faqs', on_delete=models.CASCADE)
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question
    
    
class SiteConfig(models.Model):
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='platform/logo/', blank=True, null=True)
    favicon = models.ImageField(upload_to='platform/favicon/', blank=True, null=True)
    language = models.CharField(max_length=50, default='en', choices=LANGUAGE_CHOICES)
    currency = models.CharField(max_length=10, default='USD', choices=CURRENCY_CHOICES)
    phone_numbers = models.JSONField(default=list, blank=True)
    email_addresses = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Site Config"
        verbose_name_plural = "Site Configs"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            SiteConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()
