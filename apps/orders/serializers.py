from rest_framework import serializers
from apps.orders.models import *
from rest_framework import serializers
from .models import Wishlist, WishlistItem

class AddToCartSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()

    def validate_course_id(self, value):
        try:
            course = Course.objects.get(id=value)
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found.")
        return value
    
    
class CartItemDetailSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source='course.id', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_price = serializers.DecimalField(source='course.price', max_digits=10, decimal_places=2, read_only=True)
    course_discount_price = serializers.DecimalField(source='course.discount_price', max_digits=10, decimal_places=2, read_only=True)
    thumbnail = serializers.ImageField(source='course.advance_info.thumbnail', read_only=True)
    rating = serializers.DecimalField(source='course.rating', max_digits=10, decimal_places=2, read_only=True)
    reviews_count = serializers.IntegerField(source='course.reviews_count', read_only=True)

    class Meta:
        model = CartItems
        fields = [
            'id',
            'course_id',
            'course_title',
            'course_price',
            'course_discount_price',
            'course_amount',
            'thumbnail',
            'rating',
            'reviews_count',
            'created_at',
        ]
        
        
        
#Wishlist serializer
class WishlistItemSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source='course.id', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    original_price = serializers.DecimalField(source='course.price',max_digits=10,decimal_places=2,read_only=True)
    rating=serializers.DecimalField(source='course.rating',max_digits=10,decimal_places=2,read_only=True)
    reviews_count=serializers.IntegerField(source='course.reviews_count',read_only=True)
    thumbnail = serializers.ImageField(source='course.advance_info.thumbnail', read_only=True)
    instructor = serializers.CharField(source='course.instructor.name', read_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            'id',
            'course_id',
            'course_title',
            'original_price',
            'thumbnail',
            'rating',
            'instructor',
            'reviews_count',
            'added_at',
        ]


class WishlistViewSerializer(serializers.ModelSerializer):
    total_items = serializers.SerializerMethodField()
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'total_items',  'items', 'created_at']

    def get_total_items(self, obj):
        return obj.items.count()

    
    
    
