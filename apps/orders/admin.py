from django.contrib import admin
from .models import Coupon,Order,OrderItem,Wishlist,WishlistItem,OrderItem

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code","discount_type",'discount_value','max_uses','used_count','min_order_amount','is_active','valid_to')
    search_fields = ("code",)
    
    
    
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id","user","status","coupon","subtotal","total_amount","discount_amount","created_at")
    search_fields = ("order_id","user__full_name")
    list_filter = ("status",)
 
 
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order","course","original_price","paid_price","created_at")
    search_fields = ("order__order_id","course__title")
    list_filter = ("created_at",)
    
    
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user","created_at")
    search_fields = ("user__full_name",)
    list_filter = ("created_at",)
    
    
@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("wishlist","course","added_at")
    search_fields = ("wishlist__user__full_name","course__title")
    list_filter = ("added_at",)