from rest_framework import serializers
from apps.core.models import Contact, FAQ, FAQCategory, SiteConfig


# Core app serializers
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class ContactStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['status']
        
        
class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class FAQCategorySerializer(serializers.ModelSerializer):
    faqs = FAQSerializer(many=True, read_only=True)

    class Meta:
        model = FAQCategory
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
        
        
class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']