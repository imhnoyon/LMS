from rest_framework import serializers
from apps.orders.models import *


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

    class Meta:
        model = CartItems
        fields = [
            'id',
            'course_id',
            'course_title',
            'course_price',
            'course_discount_price',
            'course_amount',
            'created_at',
        ]