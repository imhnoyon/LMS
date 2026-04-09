import django
from rest_framework import serializers
from django.db import transaction
from apps.affiliates.models import *
from apps.payments.models import Commission
from apps.users.models import User
from django.db.models import Sum

class AffiliateRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    affiliate_type = serializers.ChoiceField(choices=Affiliate.AFFILIATE_TYPE_CHOICES,required=True)
    iban = serializers.CharField(required=True, allow_blank=True)
    tax_id = serializers.CharField(required=True, allow_blank=True)
    address = serializers.CharField(required=True, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "password",
            "confirm_password",
            "affiliate_type",
            "iban",
            "tax_id",
            "address",
            "accepted_terms",
        ]
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

        affiliate_type = validated_data.pop("affiliate_type")
        iban = validated_data.pop("iban", "")
        tax_id = validated_data.pop("tax_id", "")
        address = validated_data.pop("address", "")

        user = User.objects.create_user(
            name=validated_data["name"],
            email=validated_data["email"],
            password=validated_data["password"],
            accepted_terms=validated_data["accepted_terms"],
            role="affiliate"
        )

        Affiliate.objects.create(
            user=user,
            affiliate_type=affiliate_type,
            iban=iban,
            tax_id=tax_id,
            address=address
        )

        return user



# Serializer for listing affiliates with user details
class AffiliateListSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Affiliate
        fields = ["id","user_id","name","email","affiliate_type", "iban","tax_id","address","commission_rate","total_earned","total_paid","total_payable","status","created_at","updated_at",]

    def get_name(self, obj):
        return obj.user.name or obj.user.email
    

# Serializer for updating affiliate status
class AffiliateStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Affiliate
        fields = ["status"]

    def validate_status(self, value):
        valid_statuses = [choice[0] for choice in Affiliate.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError("Invalid status selected.")
        return value
    
    
    
# Serializer for affiliate 
class AffiliateCourseListSerializer(serializers.ModelSerializer):
    course_thumbnail = serializers.ImageField(source="advance_info.thumbnail", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Course
        fields = ["id", "title",'subtitle',  "category_name", "price",'discount_price', "course_thumbnail", "created_at"]
        
        
        
        


         
    
    
        
    

# Serializer for affiliate commissions in history
class AffiliateCommissionHistorySerializer(serializers.ModelSerializer):
    order_id = serializers.SerializerMethodField()
    course_title = serializers.CharField(source="product.title", read_only=True)
    customer_name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    commission_amount = serializers.DecimalField(source="commission_rate", max_digits=10, decimal_places=2, read_only=True)
    commission_percentage = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at", format="%b %d, %Y", read_only=True)

    class Meta:
        model = AffiliateCommission
        fields = [
            "id", "order_id", "course_title", "customer_name", 
            "price", "commission_percentage", "commission_amount", 
            "status", "date"
        ]

    def get_order_id(self, obj):
        return obj.order.order_id if obj.order else "N/A"

    def get_customer_name(self, obj):
        return obj.order.user.name if obj.order and obj.order.user else "Unknown"

    def get_price(self, obj):
        return obj.order.total_amount if obj.order else "0.00"

    def get_commission_percentage(self, obj):
        return f"{int(obj.affiliate.commission_rate * 100)}%"
    
    
    
    
    
class AffiliateProfileSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","name","email","phone","avatar","is_verified","created_at","updated_at",]
        read_only_fields = ["id","email","is_verified","created_at","updated_at",]