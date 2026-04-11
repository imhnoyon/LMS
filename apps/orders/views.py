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
    # permission_classes = [IsAuthenticated, IsStudent]
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

        referral_code = request.data.get("referral_code")

        amount = course.price if getattr(course, "price", None) else course.price
        CartItems.objects.create(
            cart=cart,
            course=course,
            course_amount=amount,
            referral_code=referral_code
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
        coupon_code = (request.data.get("coupon_code") or "").strip()

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

        # 🔹 NEW logic: Capture referral code from request to apply it to order items
        global_referral_code = (request.data.get("referral_code") or "").strip()

        # 🔹 Try to find a global coupon (Order-wide)
        global_coupon = None
        if coupon_code:
            global_coupon = Coupon.objects.filter(code=coupon_code).first()
            if global_coupon and not global_coupon.is_valid():
                global_coupon = None

        created_items = []
        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        matched_any_coupon = False
        processed_courses = set()

        # Phase 1: Calculate base prices and course-specific coupons
        for item in cart_items:
            course = item.course
            if course.id in processed_courses: continue
            processed_courses.add(course.id)

            # Skip Logic
            if Enrollment.objects.filter(user=user, course=course).exists() or course.instructor == user:
                continue
            if course.status not in ["accepted", "featured"]:
                continue

            original_price = Decimal(course.price)
            paid_price = original_price
            course_discount = Decimal("0.00")

            # Check Course-Specific Coupon
            course_coupon = (course.coupon_code or "").strip().lower()
            if coupon_code and course_coupon == coupon_code.lower() and course.is_coupon_valid():
                matched_any_coupon = True
                if course.discount_price is not None:
                    # Logic: discount_price is the FINAL PRICE to pay (e.g. 750.00)
                    paid_price = Decimal(course.discount_price)
                    course_discount = original_price - paid_price

            if paid_price < 0: paid_price = 0

            # Prioritize the code passed in the API request over the one already in the cart
            final_referral_code = global_referral_code if global_referral_code else item.referral_code

            OrderItem.objects.create(
                order=order, course=course,
                original_price=original_price, paid_price=paid_price,
                referral_code=final_referral_code
            )

            subtotal += original_price
            total_discount += course_discount
            created_items.append({
                "course_id": course.id,
                "course_title": course.title,
                "original_price": str(original_price),
                "discount_amount": str(course_discount),
                "paid_price": str(paid_price)
            })

        if not created_items:
            order.delete()
            return APIResponse.error(message="No valid courses found in cart.", status_code=400)

        # Phase 2: Apply Global Coupon if no course coupon matched
        if global_coupon and not matched_any_coupon:
            matched_any_coupon = True
            if global_coupon.discount_type == "flat":
                total_discount = global_coupon.discount_value
            else: 
                total_discount = (subtotal * global_coupon.discount_value) / 100
            
            
            if total_discount > subtotal: total_discount = subtotal
            
            global_coupon.used_count += 1
            global_coupon.save(update_fields=['used_count'])

        # Final Verification
        if coupon_code and not matched_any_coupon:
            order.delete()
            return APIResponse.error(message="Invalid or expired coupon code.", status_code=400)

        total_amount = subtotal - total_discount
        if total_amount < 0: total_amount = 0

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