from django.urls import path
from apps.orders.views import *


# Orders app URLs
urlpatterns = [
     path("cart/add/", AddToCartView.as_view(), name="cart-add"),
     path("cart-view/", CartListView.as_view(), name="cart-list"),
]