from rest_framework import serializers
from django.db import transaction
from apps.courses.models import sessionRecordUploader
from apps.users.models import User
from apps.organizations.models import Membership, Organization, Invitation
from django.utils.timesince import timesince

class OrganizationRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    organization_name = serializers.CharField(source="organization.name", required=True)

    class Meta:
        model = User
        fields = ["name","email","password","confirm_password","organization_name","accepted_terms",]
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
            role="Or_admin",
          
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


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "organization", "invited_by", "email", "role", "token", "status", "created_at", "expires_at"]
        read_only_fields = ["id", "organization", "invited_by", "token", "status", "created_at", "expires_at"]

    def validate(self, attrs):
        email = attrs.get("email").lower().strip()
        organization = self.context.get("organization")

        if not organization:
             raise serializers.ValidationError({"organization": "Organization context is missing."})

        # Check if user is already a member
        if Membership.objects.filter(organization=organization, user__email=email).exists():
            raise serializers.ValidationError({"email": "This user is already a member of this organization."})

        # Check for pending invitation
        if Invitation.objects.filter(organization=organization, email=email, status=Invitation.Status.PENDING).exists():
            raise serializers.ValidationError({"email": "A pending invitation already exists for this email in this organization."})

        return attrs
    

# Serializer for organization membership details    
class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_avatar = serializers.ImageField(source="user.avatar", read_only=True)
    last_login = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    class Meta:
        model = Membership
        fields = [
            "id",
            "organization_name",
            "user",
            "user_name",
            "user_email",
            "user_avatar",
            "role",
            "status",
            "last_login",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "organization_name",
            "user",
            "joined_at",
        ]

    def get_last_login(self, obj):
        if obj.user.last_login:
            return f"{timesince(obj.user.last_login)} ago"
        return "Never"
    
    
    
    
    
class LiveSessionUploaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = sessionRecordUploader
        fields = ["id","course_name", "title", "recording_file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]
        
        
        
    