from django.urls import path

from . import views

app_name = "carts"

urlpatterns = [
    path("", views.CartDetailView.as_view(), name="cart-detail"),
    path("items/", views.CartItemListCreateView.as_view(), name="cart-item-create"),
    path("items/<int:item_id>/", views.CartItemDetailView.as_view(), name="cart-item-detail"),
    path("clear/", views.CartClearView.as_view(), name="cart-clear"),
    path("merge/", views.CartMergeView.as_view(), name="cart-merge"),
]
