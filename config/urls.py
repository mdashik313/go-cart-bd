"""
Project-level URL configuration
"""

from django.contrib import admin
from django.urls import include, path

from users.urls import address_urlpatterns, auth_urlpatterns
from products.urls import category_urlpatterns, product_urlpatterns, inventory_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include((auth_urlpatterns, "auth"))),
    path("api/users/", include((address_urlpatterns, "user-addresses"))),
    path("api/categories/", include((category_urlpatterns, "categories"))),
    path("api/products/", include((product_urlpatterns, "products"))),
    path("api/inventory/", include((inventory_urlpatterns, "inventory"))),
]
