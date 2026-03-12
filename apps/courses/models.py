from django.db import models
from users.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Course Category Model--------
class Category(models.Model):
    CHOICES=[
            ('certified', 'Certified'),
            ('popular', 'Popular'),
            ('none', 'None')
        ]
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=20)   # Like MED-01, EDU-02
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True, null=True)
    badge = models.CharField(max_length=50,choices=CHOICES,default='none')
    
    
# Sub-Category Model-------
class SubCategory(models.Model):
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="subcategories")
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
# Course Model --------
class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('bangla', 'Bangla'),
    ]
    CHOICES=[
            ('draft', 'Draft'),
            ('pending', 'Pending Review'),
            ('published', 'Published')
        ]
    title = models.CharField(max_length=80)
    subtitle = models.CharField(max_length=120)
    
    instructor = models.ForeignKey(User,on_delete=models.CASCADE,related_name='instructor_courses')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    sub_category = models.ForeignKey(SubCategory,on_delete=models.SET_NULL,null=True,blank=True)
    
    topic = models.CharField(max_length=200)
    language = models.CharField(max_length=20,choices=LANGUAGE_CHOICES, default='english')
    level = models.CharField(max_length=20,choices=LEVEL_CHOICES)
    price = models.DecimalField(max_digits=8,decimal_places=2)
    discount_price = models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True)
    coupon_code = models.CharField(max_length=50,blank=True,null=True)
    coupon_expiry = models.CharField(max_length=50,blank=True,null=True)
    thumbnail = models.ImageField(upload_to="courses/thumbnails/",null=True,blank=True)
    trailer_video = models.FileField(upload_to="courses/trailers/",null=True,blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20,choices=CHOICES,default='draft')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    
# Course Learning ---- 
class CourseLearning(models.Model):
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name="learnings")
    title = models.CharField(max_length=120)
    
    
# Course Requirements ----
class CourseRequirement(models.Model):
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name="requirements")
    title = models.CharField(max_length=120)
    
    
# Course Section Model ----
class CourseSection(models.Model):
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name="sections")
    title = models.CharField(max_length=255)


# Lecture Model ----
class Lecture(models.Model):
    section = models.ForeignKey(CourseSection,on_delete=models.CASCADE,related_name="lectures")
    title = models.CharField(max_length=255)
    video = models.FileField(upload_to="courses/lectures/")

# Course Comment Model ----
class Comment(models.Model):
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name="comments")
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="comments")
    message = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
# Reviews model ------
class Review(models.Model):
    course=models.ForeignKey(Course,on_delete=models.CASCADE, related_name="reviews")
    user=models.ForeignKey(User,on_delete=models.CASCADE , related_name="reviews")
    ratings=models.PositiveIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    feedback=models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["course", "user"]



# Live class or session -----
class LiveSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    ]
    lecture = models.OneToOneField(Lecture, on_delete=models.CASCADE, related_name='live_session')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    meeting_url = models.URLField()          # Zoom/Google Meet link
    meeting_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    recording_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = 'live_sessions'
 
    def __str__(self):
        return f"Live: {self.title} at {self.scheduled_at}"


   
"""
Written by Mahedi Hasan Noyon
"""