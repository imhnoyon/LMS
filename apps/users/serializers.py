from rest_framework import serializers
from apps.users.models import User

# Serializer for listing users with course count
class UserListSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(source='courses.count', read_only=True)
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
            "created_at",
        ]
        
# Serializer for user details   
class UserDetailSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        ]