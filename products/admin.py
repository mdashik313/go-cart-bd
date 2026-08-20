from django.contrib import admin

from .models import Category, InventoryTransaction, Product, ProductImage, ProductVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "is_active", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "price", "stock_quantity", "is_active", "is_featured", "created_at"]
    list_filter = ["category", "is_active", "is_featured"]
    search_fields = ["name", "sku"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "alt_text", "is_primary", "sort_order"]
    list_filter = ["is_primary"]
    search_fields = ["product__name", "alt_text"]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["sku", "product", "price", "stock_quantity", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["sku", "product__name"]


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "product", "variant", "transaction_type", "quantity",
        "previous_stock", "new_stock", "reference", "created_at", "created_by",
    ]
    list_filter = ["transaction_type", "created_at"]
    search_fields = ["product__name", "variant__sku", "reference"]
