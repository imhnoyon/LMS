import django
from rest_framework import serializers
from django.db import transaction
from apps.affiliates.models import *
from apps.users.models import User


class AffiliateRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    company_name = serializers.CharField(source="Affiliate.company_name", required=True)
    affiliate_type = serializers.ChoiceField(choices=Affiliate.AFFILIATE_TYPE_CHOICES, required=True)
    account_number = serializers.CharField(source="Affiliate.account_number", required=True)
    tax_id = serializers.CharField(source="Affiliate.tax_id", required=True)
    address = serializers.CharField(source="Affiliate.address", required=True)
    
    class Meta:
        model=User
        fields=["full_name","email","password","confirm_password","company_name","affiliate_type","account_number","tax_id","address","is_terms_service",]
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
        affiliate_data = validated_data.pop("Affiliate")
        company_name = affiliate_data["company_name"]
        affiliate_type = affiliate_data["affiliate_type"]
        account_number = affiliate_data["account_number"]
        tax_id = affiliate_data["tax_id"]
        address = affiliate_data["address"]

        user = User.objects.create_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_terms_service=validated_data["is_terms_service"],
            role="affiliate"
        )
        Affiliate.objects.create(
            user=user,
            company_name=company_name,
            affiliate_type=affiliate_type,
            account_number=account_number,
            tax_id=tax_id,
            address=address
        )
        return user
