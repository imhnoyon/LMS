from rest_framework import serializers
from django.db import transaction
from apps.users.models import User
from apps.organizations.models import Organization

class OrganizationRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    organization_name = serializers.CharField(source="organization.name", required=True)

    class Meta:
        model = User
        fields = ["full_name","email","password","confirm_password","organization_name","is_terms_service",]
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8}
        }
    def validate_full_name(self, value):
        if User.objects.filter(full_name=value).exists():
            raise serializers.ValidationError("Full name already exists.")
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
        if not attrs.get("is_terms_service", False):
            raise serializers.ValidationError({
                "is_terms_service": "You must accept the terms and conditions."
            })
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        organization_data = validated_data.pop("organization")
        organization_name = organization_data["name"]

        user = User.objects.create_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_terms_service=validated_data["is_terms_service"],
            role="organization"
        )
        Organization.objects.create(
            owner=user,   
            name=organization_name,
        )
        return user