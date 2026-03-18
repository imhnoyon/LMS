from symtable import Class

from django.contrib import admin
from .models import Category, Course,CourseAdvanceInfo,CourseOutcome,CourseRequirement,Section,Lecture,LectureVideo,LectureAttachment,LectureCaption,LectureNoteFile,Quiz,Question,QuestionOption,TrueFalseAnswer,Comment,Review,LiveClass,LiveClassAttendance

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name','slug','description', 'created_at')
    search_fields = ('name',)
    
    
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title','subtitle', 'category', 'instructor','topic','language','level','price','discount_price','coupon_code','status', 'created_at')
    list_filter = ('category', 'instructor', 'created_at')
    search_fields = ('title', 'subtitle', 'description')
    

@admin.register(CourseAdvanceInfo)
class CourseAdvanceInfoAdmin(admin.ModelAdmin):
    list_display = ('course','thumbnail','trailer_video', 'description',)
    list_filter = ('course', )
    search_fields = ('course__title',)

@admin.register(CourseOutcome)
class CourseOutcomeAdmin(admin.ModelAdmin):
    list_display = ('course', 'text','order')
    list_filter = ('course',)
    search_fields = ('text',)

@admin.register(CourseRequirement)
class CourseRequirementAdmin(admin.ModelAdmin):
    list_display = ('course', 'text','order')
    list_filter = ('course',)
    search_fields = ('text',)
    
    
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('course', 'name', 'order')
    list_filter = ('course',)
    search_fields = ('name',)
    
    
    
@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ('section', 'name', 'order','description','notes_text')
    list_filter = ('section',)
    search_fields = ('name',)

@admin.register(LectureVideo)
class LectureVideoAdmin(admin.ModelAdmin):
    list_display = ('lecture','video_file','duration')
    list_filter =('lecture',)
    search_fields = ('lecture__name',)
    
@admin.register(LectureAttachment)
class LectureAttachmentAdmin(admin.ModelAdmin):
    list_display = ('lecture','file','name')
    list_filter =('lecture',)
    search_fields = ('lecture__name',)
    
    
@admin.register(LectureCaption)
class LectureCaptionAdmin(admin.ModelAdmin):
    list_display = ('lecture','language','file')
    list_filter =('lecture',)
    search_fields = ('lecture__name',)
    
    
    
@admin.register(LectureNoteFile)
class LectureNoteFileAdmin(admin.ModelAdmin):
    list_display = ('lecture','file','name')
    list_filter =('lecture',)
    search_fields = ('lecture__name',)
    
    
    
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('lecture', 'section', 'title','description','time_limit_minutes','attempts_allowed','passing_score','shuffle_questions')
    list_filter = ('lecture','section',)
    search_fields = ('title',)
    
    
    
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'text','question_type','order')
    list_filter = ('quiz',)
    search_fields = ('text',)
    
    
    
@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ('question', 'text','is_correct','order')
    list_filter = ('question',)
    search_fields = ('is_correct',)
    
    
@admin.register(TrueFalseAnswer)
class TrueFalseAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'correct_answer')
    list_filter = ('question',)
    search_fields = ('correct_answer',)
    
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display =('course','user','parent','text','created_at','updated_at')
    list_filter =('course','user',)
    search_fields =('user__full_name',)
    
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('course','user','rating','comment','created_at','updated_at')
    list_filter=('course','user',)
    
    
@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ('course','title','instructor','topic','scheduled_date','scheduled_time','duration_minutes','platform','class_link','is_recorded','recording_link')
    list_filter = ('course',)
    search_fields = ('title',)
    
    
@admin.register(LiveClassAttendance)
class LiveClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('live_class', 'student','status', 'joined_at','left_at')
    list_filter = ('live_class', 'student')