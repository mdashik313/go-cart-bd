"""
Project-level URL configuration
"""

from django.contrib import admin
from django.urls import include, path

from users.urls import address_urlpatterns, auth_urlpatterns
from products.urls import (
    category_urlpatterns,
    product_urlpatterns,
    inventory_urlpatterns,
)
from carts.urls import urlpatterns as cart_urlpatterns
from orders.urls import admin_urlpatterns, checkout_urlpatterns, customer_urlpatterns
from payments.urls import admin_urlpatterns as payment_admin_urlpatterns, webhook_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include((auth_urlpatterns, "auth"))),
    path("api/users/", include((address_urlpatterns, "user-addresses"))),
    path("api/categories/", include((category_urlpatterns, "categories"))),
    path("api/products/", include((product_urlpatterns, "products"))),
    path("api/inventory/", include((inventory_urlpatterns, "inventory"))),
    path("api/cart/", include((cart_urlpatterns, "cart"))),
    path("api/checkout/", include((checkout_urlpatterns, "checkout"))),
    path("api/orders/", include((customer_urlpatterns, "orders"))),
    path("api/admin/orders/", include((admin_urlpatterns, "admin-orders"))),
    path("api/payments/", include((webhook_urlpatterns, "payments"))),
    path("api/admin/payments/", include((payment_admin_urlpatterns, "admin-payments"))),
]
