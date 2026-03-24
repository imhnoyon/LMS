from time import timezone

from rest_framework import serializers
from apps.instructors.models import Instructor
from apps.organizations.models import Invitation, Membership
from apps.users.models import User

class InstructorRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["name", "email", "password", "confirm_password", "accepted_terms"]
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8}
        }
    def validate_name(self, value):
        if User.objects.filter(name=value).exists():
            raise serializers.ValidationError("Name already exists.")
        return value
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        if not attrs.get("accepted_terms", False):
            raise serializers.ValidationError({
                "accepted_terms": "You must accept the terms and conditions."
            })
             
        return attrs
    
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data.pop("invite_token", None)
        user = User.objects.create_user(
            name=validated_data["name"],
            email=validated_data["email"],
            password=validated_data["password"],
            accepted_terms=validated_data["accepted_terms"],
            role="instructor"
        )
        Instructor.objects.create(user=user)
        return user
    
    
    
    

# Serializer for listing pending instructors

from apps.instructors.models import Instructor
class PendingInstructorListSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Instructor
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "phone",
            "title",
            "biography",
            "is_approved",
            "is_featured",
        ]


class ApproveInstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ["is_approved", "is_featured"]

    def update(self, instance, validated_data):
        instance.is_approved = validated_data.get("is_approved", instance.is_approved)
        instance.is_featured = validated_data.get("is_featured", instance.is_featured)
        instance.save()
        return instance
    
    
    