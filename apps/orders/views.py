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

        amount = course.price if getattr(course, "price", None) else course.price
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
        
        
from decimal import Decimal
from django.db import transaction

from decimal import Decimal
from django.db import transaction
from rest_framework.views import APIView
from rest_framework import status


class CreateOrderFromCartView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    @transaction.atomic
    def post(self, request):
        user = request.user
        coupon_code = request.data.get("coupon_code", "").strip()

        if user.role != "student":
            return APIResponse.error(
                message="Only students can place orders.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return APIResponse.error(
                message="Cart is empty.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        cart_items = cart.cart_items.select_related("course", "course__instructor")

        if not cart_items.exists():
            return APIResponse.error(
                message="Your cart is empty.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.create(
            user=user,
            status="pending",
            coupon_code=coupon_code if coupon_code else None
        )

        created_items = []

        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_amount = Decimal("0.00")

        matched_coupon = False
        processed_courses = set()

        for item in cart_items:
            course = item.course

            if course.id in processed_courses:
                continue
            processed_courses.add(course.id)

            if Enrollment.objects.filter(user=user, course=course).exists():
                continue

            if course.instructor == user:
                continue

            if course.status not in ["published", "accepted", "featured"]:
                continue

            original_price = Decimal(course.price)

            # ----------------------------
            # DEFAULT VALUES
            # ----------------------------
            discount_amount = Decimal("0.00")
            paid_price = original_price

            # ----------------------------
            # COUPON LOGIC (FIXED)
            # ----------------------------
            if (
                coupon_code
                and course.coupon_code
                and course.coupon_code.lower() == coupon_code.lower()
                and course.is_coupon_valid()
            ):
                matched_coupon = True

                # FIX: treat discount_price as DISCOUNT, NOT final price
                if course.discount_price is not None:
                    discount_amount = Decimal(course.discount_price)

                # prevent overflow
                if discount_amount > original_price:
                    discount_amount = original_price

                paid_price = original_price - discount_amount

            # safety
            if paid_price < Decimal("0.00"):
                paid_price = Decimal("0.00")

            # ----------------------------
            # CREATE ORDER ITEM
            # ----------------------------
            OrderItem.objects.create(
                order=order,
                course=course,
                original_price=original_price,
                paid_price=paid_price
            )

            # ----------------------------
            # TOTALS (CORRECT)
            # ----------------------------
            subtotal += original_price
            total_discount += discount_amount
            total_amount += paid_price

            created_items.append({
                "course_id": course.id,
                "course_title": course.title,
                "original_price": str(original_price),
                "discount_amount": str(discount_amount),
                "paid_price": str(paid_price),
                "course_coupon_code": course.coupon_code or ""
            })

        if not created_items:
            order.delete()
            return APIResponse.error(
                message="No valid courses found in cart for order.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if coupon_code and not matched_coupon:
            order.delete()
            return APIResponse.error(
                message="Invalid or expired coupon code.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        order.subtotal = subtotal
        order.discount_amount = total_discount
        order.total_amount = total_amount
        order.save(update_fields=["subtotal", "discount_amount", "total_amount", "coupon_code"])

        cart.cart_items.all().delete()

        return APIResponse.success(
            message="Order created from cart successfully.",
            data={
                "order_id": order.id,
                "custom_order_id": order.order_id,
                "status": order.status,
                "coupon_code": order.coupon_code,
                "subtotal": str(order.subtotal),
                "discount_amount": str(order.discount_amount),
                "total_amount": str(order.total_amount),
                "items": created_items
            },
            status_code=status.HTTP_201_CREATED
        )
        

# Add Wishlist course
class AddToWishlistView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return APIResponse.error(
                message="Course not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        wishlist, created = Wishlist.objects.get_or_create(user=request.user)

        if WishlistItem.objects.filter(wishlist=wishlist, course=course).exists():
            return APIResponse.error(
                message="Course already exists in wishlist.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        WishlistItem.objects.create(wishlist=wishlist, course=course)

        return APIResponse.success(
            message="Course added to wishlist successfully.",
            data={
                "course_id": course.id,
                "course_title": course.title
            },
            status_code=status.HTTP_201_CREATED
        )
        
        
# Wishlist view list
class WishlistViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)

        wishlist = Wishlist.objects.prefetch_related('items__course').get(user=request.user)

        serializer = WishlistViewSerializer(wishlist, context={'request': request})

        return APIResponse.success(
            message="Wishlist retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
    def delete(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return APIResponse.error(
                message="Course not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        wishlist, created = Wishlist.objects.get_or_create(user=request.user)

        if not WishlistItem.objects.filter(wishlist=wishlist, course=course).exists():
            return APIResponse.error(
                message="Course not found in wishlist.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        WishlistItem.objects.filter(wishlist=wishlist, course=course).delete()

        return APIResponse.success(
            message="Course removed from wishlist successfully.",
            data={},
            status_code=status.HTTP_200_OK
        )