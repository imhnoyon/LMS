from django.contrib import admin
from .models import Category, Course
# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    
    
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'instructor', 'created_at')
    list_filter = ('category', 'instructor', 'created_at')
    search_fields = ('title', 'description')
    
