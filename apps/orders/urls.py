from django.urls import path
from apps.orders.views import *


# Orders app URLs
urlpatterns = [
     
     # Student deshboard
     path("cart/add/", AddToCartView.as_view(), name="cart-add"),
     path("cart-view/", CartListView.as_view(), name="cart-list"),
     path("cart-remove/<int:item_id>/", CartListView.as_view(), name="cart-remove-items"),
     path("cart/checkout/", CreateOrderFromCartView.as_view(), name="cart-checkout"),
     path('wishlist/add/<int:course_id>/', AddToWishlistView.as_view(), name='wishlist-add'),
      path('wishlist/', WishlistViewAPIView.as_view(), name='wishlist-view'),
      path('wishlist/<int:course_id>/', WishlistViewAPIView.as_view(), name='wishlist-view'),
]