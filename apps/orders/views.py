from django.shortcuts import render
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.enrollments.models import *
from apps.courses.models import *
from .serializers import *
from utils.api_response import APIResponse
from utils.permissions import IsStudent



class AddToCartView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    @transaction.atomic
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        course_id = serializer.validated_data["course_id"]

        course = Course.objects.get(id=course_id)

        if user.role != "student":
            return APIResponse.error(
                message="Only students can add courses to cart.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        if course.instructor == user:
            return APIResponse.error(
                message="You cannot add your own course to cart.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if Enrollment.objects.filter(user=user, course=course).exists():
            return APIResponse.error(
                message="You are already enrolled in this course.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        cart, _ = Cart.objects.get_or_create(user=user)

        if CartItems.objects.filter(cart=cart, course=course).exists():
            return APIResponse.error(
                message="Course already added to cart.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        amount = course.discount_price if getattr(course, "discount_price", None) else course.price
        CartItems.objects.create(
            cart=cart,
            course=course,
            course_amount=amount
        )

        return APIResponse.success(
            message="Course added to cart successfully.",
            data={
                "course_id": course.id,
                "course_title": course.title,
                "course_amount": str(amount)
            },
            status_code=status.HTTP_201_CREATED
        )
        
        
class CartListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.cart_items.select_related("course").order_by("-id")

        serializer = CartItemDetailSerializer(cart_items, many=True)

        subtotal = sum(item.course_amount for item in cart_items)

        return APIResponse.success(
            message="Cart retrieved successfully.",
            data={
                "cart_id": cart.id,
                "total_items": cart_items.count(),
                "subtotal": str(subtotal),
                "items": serializer.data
            },
            status_code=200
        )
        
        
    def delete(self, request, item_id):
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItems.objects.get(id=item_id, cart=cart)
        except Cart.DoesNotExist:
            return APIResponse.error(
                message="Cart not found.",
                status_code=404
            )
        except CartItems.DoesNotExist:
            return APIResponse.error(
                message="Cart item not found.",
                status_code=404
            )

        cart_item.delete()

        return APIResponse.success(
            message="Cart item removed successfully.",
            data={},
            status_code=200
        )