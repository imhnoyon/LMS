from rest_framework import serializers
from django.db import transaction
from apps.users.models import User
from apps.organizations.models import Membership, Organization

class OrganizationRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    organization_name = serializers.CharField(source="organization.name", required=True)

    class Meta:
        model = User
        fields = ["name","email","password","confirm_password","organization_name","accepted_terms",]
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
    
    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        organization_data = validated_data.pop("organization")
        organization_name = organization_data["name"]

        user = User.objects.create_user(
            name=validated_data["name"],
            email=validated_data["email"],
            password=validated_data["password"],
            accepted_terms=validated_data["accepted_terms"],
            role="owner",
          
        )
        organization=Organization.objects.create(  
            name=organization_name,
        )
        Membership.objects.create(
            organization=organization,
            user=user,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )
        return user
    
    
    
# Organization unverified list serializer
class UnverifiedOrganizationListSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id","name","bio","photo","banner","phone","email","rating","total_reviews","total_students","total_courses","is_active","is_verified","owner_name","owner_email","created_at","updated_at",]

    def get_owner_name(self, obj):
        owner_membership = obj.owner
        if owner_membership and owner_membership.user:
            return owner_membership.user.name
        return None

    def get_owner_email(self, obj):
        owner_membership = obj.owner
        if owner_membership and owner_membership.user:
            return owner_membership.user.email
        return None