from django.urls import path

from . import views

app_name = "products"

category_urlpatterns = [
    path("", views.CategoryListCreateView.as_view(), name="category-list-create"),
    path("<slug:slug>/", views.CategoryDetailView.as_view(), name="category-detail"),
]

product_urlpatterns = [
    path("", views.ProductListCreateView.as_view(), name="product-list-create"),
    path("featured/", views.FeaturedProductsView.as_view(), name="product-featured"),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("<slug:slug>/images/", views.ProductImageUploadView.as_view(), name="product-image-upload"),
]

inventory_urlpatterns = [
    path("adjust/", views.InventoryAdjustView.as_view(), name="inventory-adjust"),
]
