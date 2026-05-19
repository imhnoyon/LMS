from rest_framework import serializers
from apps.users.models import User
from django.utils.timesince import timesince
# Serializer for listing users with course count
class UserListSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(source='courses.count', read_only=True)
    last_active = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "is_active",
            "is_verified",
            "avatar",
            "course_count",
            "last_active",
            "created_at",
        ]
        
    def get_last_active(self, obj):
        if obj.last_login:
            return timesince(obj.last_login) + " ago"
        return "Never"
        
# Serializer for user details   
class UserDetailSerializer(serializers.ModelSerializer):
    last_active = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "phone",
            "avatar",
            "is_active",
            "is_verified",
            "accepted_terms",
            "last_active",
            "created_at",
            "updated_at",
        ]
    def get_last_active(self, obj):
        if obj.last_login:
            return timesince(obj.last_login) + " ago"
        return "Never"
    
    

# Serializer for user sending emails 
class SendEmailSerializer(serializers.Serializer):
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
    
    
    
    
class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name","email","role", "phone",'avatar']