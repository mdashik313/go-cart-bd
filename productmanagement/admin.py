from django.contrib import admin

# Register your models here.
from .models import Product, ProductCategory


class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "stock",
        "is_active",
        "created_by",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")


admin.site.register(ProductCategory, ProductCategoryAdmin)
admin.site.register(Product, ProductAdmin)