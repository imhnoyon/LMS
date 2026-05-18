from rest_framework import serializers
from django.db import transaction
from apps.courses.models import Course, sessionRecordUploader
from apps.payments.models import Withdrawal
from apps.users.models import User
from apps.organizations.models import Contract, Membership, Organization, Invitation
from django.utils import timezone
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
        fields = ["id","name","bio","photo","banner","phone","rating","total_reviews","total_students","total_courses","is_active","is_verified","owner_name","owner_email","created_at","updated_at",]

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
        
        
        
        
class OrganizationAdminSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id","name","bio","photo","banner","phone","rating","total_reviews","total_students","total_courses","is_active","is_verified","owner_name","owner_email","created_at","updated_at","avatar",]

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

    def get_avatar(self, obj):
        owner_membership = obj.owner
        if owner_membership and owner_membership.user and getattr(owner_membership.user, 'avatar', None):
            request = self.context.get('request')
            try:
                return request.build_absolute_uri(owner_membership.user.avatar.url) if request else owner_membership.user.avatar.url
            except Exception:
                return owner_membership.user.avatar.url
        return None

        
        
    
# Earnings serializers
class WithdrawalSerializer(serializers.ModelSerializer):
   class Meta:
        model = Withdrawal
        fields = ['id','withdraw_id', 'user_name', 'bank_name', 'bank_last4', 'amount', 'status', 'requested_at']
    
class RevenueChartSerializer2(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
class OrganizationEarningsSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_withdrawals = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    withdrawals = WithdrawalSerializer(many=True, read_only=True)
    monthly_revenue_chart = RevenueChartSerializer2(many=True)
    
    
    
    
class OrInstructorSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    class Meta:
        model = Membership
        fields = ["id","user_name","organization_name","role","status","joined_at"]
        read_only_fields = ["id","user_name","organization_name","joined_at"]
        
        
        
        
        
class OrCourseSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    class Meta:
        model = Course
        fields = ["id","title",'subtitle',"organization_name"]
        read_only_fields = ["id","title",'subtitle',"organization_name"]
        
        
class ContractSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source="instructor.user.name", read_only=True)
    course_name = serializers.CharField(source="course.title", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    instructor_avatar = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = ["id", "organization_name", "instructor_name", "course_name", "revenue_share", "expiry_date", "status", "created_at", "instructor_avatar"]
        read_only_fields = ["id", "organization_name", "instructor_name", "course_name", "status", "created_at"]

    def get_membership_id(self, obj):
        return obj.instructor.id if obj.instructor else None

    def get_status(self, obj):
        if obj.expiry_date and obj.expiry_date < timezone.now().date():
            return Contract.Status.EXPIRED
        return Contract.Status.ONGOING

    def get_instructor_avatar(self, obj):
        if obj.instructor and obj.instructor.user and getattr(obj.instructor.user, 'avatar', None):
            request = self.context.get('request')
            try:
                return request.build_absolute_uri(obj.instructor.user.avatar.url) if request else obj.instructor.user.avatar.url
            except Exception:
                return obj.instructor.user.avatar.url
        return None

class ContractCreateSerializer(serializers.ModelSerializer):
    instructor_id = serializers.IntegerField(write_only=True)
    course_id = serializers.IntegerField(write_only=True)
    revenue_share = serializers.FloatField(min_value=0, max_value=100)
    

    class Meta:
        model = Contract
        fields = ["instructor_id", "course_id", "expiry_date", "revenue_share"]

    def validate(self, attrs):
        organization = self.context.get("organization")
        if not organization:
            raise serializers.ValidationError({"organization": "Organization context is required."})

        instructor_id = attrs.get("instructor_id")
        course_id = attrs.get("course_id")
        revenue_share = attrs.get("revenue_share")

        # Validate revenue share
        if not (0 <= revenue_share <= 100):
            raise serializers.ValidationError({"revenue_share": "Revenue share must be between 0 and 100 (0-100%)."})

        # Validate instructor membership exists in this organization
        instructor_membership = Membership.objects.select_related("user").filter(
            id=instructor_id,
            organization=organization,
            role=Membership.Role.INSTRUCTOR,
            status=Membership.Status.ACTIVE,
        ).first()
        if not instructor_membership:
            raise serializers.ValidationError(
                {"instructor_id": "No active instructor found in this organization with this ID."}
            )

        # Validate course exists in this organization
        course = Course.objects.filter(
            id=course_id,
            organization=organization,
        ).first()
        if not course:
            raise serializers.ValidationError(
                {"course_id": "No course found in this organization with this ID."}
            )

        attrs["instructor_membership"] = instructor_membership
        attrs["course"] = course
        attrs["organization"] = organization
        return attrs

    def create(self, validated_data):
        instructor_membership = validated_data.pop("instructor_membership")
        course = validated_data.pop("course")
        organization = validated_data.pop("organization")

        return Contract.objects.create(
            organization=organization,
            instructor=instructor_membership,
            course=course,
            **validated_data,
        )
        
        
class OrganizationProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, allow_blank=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = Organization
        fields = ["id", "username", "name", "bio", "photo", "banner", "phone", "email"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            data["username"] = request.user.name
        else:
            data["username"] = instance.name
        return data

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Update the authenticated user's name
        username = validated_data.pop("username", None)
        if username and user:
            user.name = username
            user.save(update_fields=["name"])
            instance.name = username

        # Optional user email update if provided
        email = validated_data.pop("email", None)
        if email and user:
            user.email = email
            user.save(update_fields=["email"])

        # Update organization fields
        instance.name = validated_data.get("name", instance.name)
        instance.bio = validated_data.get("bio", instance.bio)
        instance.phone = validated_data.get("phone", instance.phone)

        # Update photo
        request = self.context.get("request")

        if request and request.FILES.get("photo"):
            instance.photo = request.FILES.get("photo")

        # Update banner
        if request and request.FILES.get("banner"):
            instance.banner = request.FILES.get("banner")

        instance.save()
        return instance


class InstructorOrganizationSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_photo = serializers.ImageField(source="organization.photo", read_only=True)
    banner = serializers.ImageField(source="organization.banner", read_only=True)
    membership_id = serializers.IntegerField(source="id", read_only=True)
    role = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)
    

    class Meta:
        model = Membership
        fields = [
            "membership_id",
            "organization_id",
            "organization_name",
            "organization_photo",
            "banner",
            "role",
            "status",
            "joined_at",
        ]
    
    
    
class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=Organization
        fields=["id","name","bio","banner",'phone','photo']
        
        
        
class InstructorContractCourseSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source="course.id", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    course_price = serializers.DecimalField(source="course.discount_price", max_digits=10, decimal_places=2, read_only=True)
    course_category = serializers.CharField(source="course.category.name", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.advance_info.thumbnail", read_only=True)

    class Meta:
        model = Contract
        fields = ["id","organization_id",'course_category',"organization_name","course_id","course_title","course_price","revenue_share","expiry_date","status",'course_thumbnail',"created_at",]
        
        
class InstructorContractCategorySerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source="course.category.id", read_only=True)
    course_category = serializers.CharField(source="course.category.name", read_only=True)

    class Meta:
        model = Contract
        fields = ['category_id','course_category',]
        
        
        
        
        
class OrganizationInstructorLiveClassDeshboardSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source="course.id", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    live_sessions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Contract
        fields = ["id","course_id","course_title","live_sessions_count"]
        
        
 