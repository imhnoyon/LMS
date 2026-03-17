from rest_framework import serializers
from apps.users.models import User


class LearnerRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ["full_name", "email", "password", "confirm_password", "is_terms_service"]
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        if not attrs.get("is_terms_service", False):
            raise serializers.ValidationError({
                "is_terms_service": "You must accept the terms and conditions."
            })
        return attrs
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_terms_service=validated_data["is_terms_service"],
            role="student"
        )
        return user