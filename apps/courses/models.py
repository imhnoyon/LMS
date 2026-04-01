from django.db import models
from apps.users.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from datetime import timedelta
from django.utils import timezone


class Category(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    slug        = models.SlugField(unique=True)
    description = models.TextField(null=True, blank=True)
    parent      = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='subcategories')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('zh', 'Chinese'),
    ]
    LEVEL_CHOICES = [
        ('beginner',     'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced',     'Advanced'),
    ]
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('published', 'Published'),
        ('archived',  'Archived'),
        ('blocked',  'Blocked'),
        ('featured',  'Featured'),
        ('accepted',  'Accepted'),
        ('rejected',  'Rejected'),
    ]
    
    EXPIRY_DURATION_CHOICES = [
    ('1_week', '1 Week'),
    ('1_month', '1 Month'),
    ('3_months', '3 Months'),
    ('lifetime', 'Lifetime'),
]

    instructor     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    title          = models.CharField(max_length=80)
    subtitle       = models.CharField(max_length=120, blank=True)
    category       = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    topic          = models.CharField(max_length=255, blank=True)
    language       = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, blank=True)
    level          = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    price          = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    coupon_code = models.CharField(max_length=50, null=True, blank=True)
    expiry_type    = models.CharField(max_length=20, choices=EXPIRY_DURATION_CHOICES, default='1_week')
    expiry_date = models.DateTimeField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def rating(self):
        if not self.reviews.exists():
            return 0
        return self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    def reviews_count(self):
        if not self.reviews.exists():
            return 0
        return self.reviews.count()
    
    def Category(self):
        if not self.category:
            return None
        return self.category.name
    
    def get_progress_percentage(self, user):
        """Calculates the course progress percentage for a specific user based on lectures."""
        total_lectures = Lecture.objects.filter(section__course=self).count()
        if total_lectures == 0:
            return 0
        
        completed_lectures = LecturesProgress.objects.filter(
            user=user, 
            course=self,
            is_completed=True
        ).count()
        
        return round((completed_lectures / total_lectures) * 100)
    
    
    def save(self, *args, **kwargs):
        if not self.expiry_date:  
            now = timezone.now()

            if self.expiry_type == '1_week':
                self.expiry_date = now + timedelta(weeks=1)

            elif self.expiry_type == '1_month':
                self.expiry_date = now + timedelta(days=30)

            elif self.expiry_type == '3_months':
                self.expiry_date = now + timedelta(days=90)

            elif self.expiry_type == 'lifetime':
                self.expiry_date = None  

        super().save(*args, **kwargs)
        
    def is_coupon_valid(self):
        if self.expiry_date is None:
            return True
        return self.expiry_date >= timezone.now()
    
    def __str__(self):
        return self.title


class CourseAdvanceInfo(models.Model):
    course        = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='advance_info')
    thumbnail     = models.ImageField(upload_to='course/thumbnails/', null=True, blank=True)
    trailer_video = models.FileField(upload_to='course/trailers/', null=True, blank=True)
    description   = models.TextField(blank=True)

    def __str__(self):
        return f"Advance Info - {self.course.title}"


class CourseOutcome(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='outcomes')
    text   = models.CharField(max_length=120)
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


class CourseRequirement(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='requirements')
    text   = models.CharField(max_length=120)
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    name   = models.CharField(max_length=255)
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.name}"


class Lecture(models.Model):
    section     = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='lectures')
    name        = models.CharField(max_length=255)
    order       = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    video_file= models.FileField(upload_to='lectures/videos/', null=True, blank=True)
    LectureAttachment = models.FileField(upload_to='lectures/attachments/', null=True, blank=True)
    LectureNoteFile= models.FileField(upload_to='lectures/notes/', null=True, blank=True)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

# I don't use this model because all fields are used in lecture model
class LectureVideo(models.Model):
    lecture    = models.OneToOneField(Lecture, on_delete=models.CASCADE, related_name='video')
    video_file = models.FileField(upload_to='lectures/videos/')
    duration   = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"Video - {self.lecture.name}"


class LectureAttachment(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='attachments')
    file    = models.FileField(upload_to='lectures/attachments/')
    name    = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Attachment - {self.lecture.name}"


class LectureCaption(models.Model):
    lecture  = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='captions')
    language = models.CharField(max_length=50)
    file     = models.FileField(upload_to='lectures/captions/')

    def __str__(self):
        return f"Caption ({self.language}) - {self.lecture.name}"


class LectureNoteFile(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='note_files')
    file    = models.FileField(upload_to='lectures/notes/')
    name    = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Note File - {self.lecture.name}"
# I don't use this model because all fields are used in lecture model ended here



# Started from quiz here
class Quiz(models.Model):
    lecture            = models.OneToOneField(Lecture, on_delete=models.CASCADE, null=True, blank=True, related_name='quiz')
    section            = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name='quizzes')
    title              = models.CharField(max_length=255)
    description        = models.TextField(blank=True)
    time_limit_minutes = models.PositiveIntegerField(default=10)
    attempts_allowed   = models.PositiveIntegerField(default=3)
    passing_score      = models.PositiveIntegerField(default=70)
    shuffle_questions  = models.BooleanField(default=False)

    def clean(self):
        if not self.lecture and not self.section:
            raise ValidationError("Quiz must belong to either a Lecture or a Section.")

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('mcq',        'Multiple Choice'),
        ('true_false', 'True or False'),
    ]

    quiz          = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='mcq')
    text          = models.TextField()
    order         = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class QuestionOption(models.Model):
    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text       = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Option: {self.text}"


class TrueFalseAnswer(models.Model):
    question       = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='true_false_answer')
    correct_answer = models.BooleanField()

    def __str__(self):
        return f"{'True' if self.correct_answer else 'False'} - {self.question}"
    


class Comment(models.Model):
    course     = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_comments')
    parent     = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.parent:
            return f"Reply by {self.user.username} on {self.course.title}"
        return f"Comment by {self.user.username} on {self.course.title}"


class Review(models.Model):
    course     = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_reviews')
    rating     = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'user')

    def __str__(self):
        return f"Review by {self.user.username} - {self.rating} Stars"


class LiveClass(models.Model):
    PLATFORM_CHOICES = [
        ('google_meet', 'Google Meet'),
        ('zoom',        'Zoom'),
    ]

    title            = models.CharField(max_length=80)
    instructor       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_classes')
    course           = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    topic            = models.TextField()
    scheduled_date   = models.DateField()
    scheduled_time   = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    platform         = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    class_link       = models.URLField()
    is_recorded      = models.BooleanField(default=False)
    recording_link   = models.URLField(blank=True, null=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.scheduled_date}"


class LiveClassAttendance(models.Model):
    STATUS_CHOICES = [
        ('attended', 'Attended'),
        ('missed',   'Missed'),
    ]

    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name='attendances')
    student    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES)
    joined_at  = models.DateTimeField(null=True, blank=True)
    left_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('live_class', 'student')

    def __str__(self):
        return f"{self.student} — {self.live_class} ({self.status})"


class LecturesProgress(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user   = models.ForeignKey(User, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_watched_at = models.DateTimeField(auto_now=True)
    watched_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["course", "user", "lecture"]


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    correct_answers = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    score_percentage = models.FloatField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        
    def course_name(self):
        return self.course.title

    def __str__(self):
        return f"{self.user} - {self.quiz.title if self.quiz else 'Quiz'} ({self.score_percentage}%)"