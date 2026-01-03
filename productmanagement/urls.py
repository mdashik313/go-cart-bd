from django.urls import path
from .views import (
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    ProductDetailView,
    ProductListView,
    CategoryCreateView,
    CategoryListView,
)

urlpatterns = [
    path("create/", ProductCreateView.as_view(), name="product-create"),
    path("list/", ProductListView.as_view(), name="product-list"),          # show all products
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),    # show single product
    path("<int:pk>/update/", ProductUpdateView.as_view(), name="product-update"),
    path("<int:pk>/delete/", ProductDeleteView.as_view(), name="product-delete"),

    # category
    path("category/create/", CategoryCreateView.as_view()),
    path("category/list/", CategoryListView.as_view()),
]