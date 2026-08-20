from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.pagination import DefaultPagination
from core.permissions import IsStaffUser
from core.response import error_response, success_response

from .models import TRANSACTION_TYPE_CHOICES, Category, InventoryTransaction, Product, ProductImage, ProductVariant
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ProductVariantSerializer,
    ProductWriteSerializer,
)

ORDERING_OPTIONS = {
    "price_asc": "price",
    "price_desc": "-price",
    "newest": "-created_at",
    "name": "name",
}


class CategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsStaffUser()]
        return [AllowAny()]

    def get(self, request):
        categories = Category.objects.filter(is_active=True).select_related("parent")
        return success_response(
            "Categories retrieved successfully.",
            CategorySerializer(categories, many=True).data,
        )

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        category = serializer.save()
        return success_response(
            "Category created successfully.",
            CategorySerializer(category).data,
            status.HTTP_201_CREATED,
        )


class CategoryDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsStaffUser()]

    def get_object(self, slug, request):
        queryset = Category.objects.all()
        if request.method == "GET":
            queryset = queryset.filter(is_active=True)
        return get_object_or_404(queryset, slug=slug)

    def get(self, request, slug):
        category = self.get_object(slug, request)
        return success_response("Category retrieved successfully.", CategorySerializer(category).data)

    def patch(self, request, slug):
        category = self.get_object(slug, request)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        category = serializer.save()
        return success_response("Category updated successfully.", CategorySerializer(category).data)

    def delete(self, request, slug):
        category = self.get_object(slug, request)
        category.is_active = False
        category.save()
        return success_response("Category deactivated successfully.")


class ProductListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsStaffUser()]
        return [AllowAny()]

    def get(self, request):
        queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related(
            "images", "variants"
        )

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search) | Q(short_description__icontains=search)
            )

        category_slug = request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        min_price = request.query_params.get("min_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = request.query_params.get("max_price")
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        featured = request.query_params.get("featured")
        if featured is not None:
            queryset = queryset.filter(is_featured=featured.lower() == "true")

        ordering = ORDERING_OPTIONS.get(request.query_params.get("ordering"), "-created_at")
        queryset = queryset.order_by(ordering)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductListSerializer(page, many=True)

        return success_response("Products retrieved successfully.", {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
        })

    def post(self, request):
        serializer = ProductWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        product = serializer.save()

        for variant_data in request.data.get("variants", []):
            variant_serializer = ProductVariantSerializer(data=variant_data)
            if not variant_serializer.is_valid():
                return error_response("Validation failed.", {"variants": variant_serializer.errors})
            variant_serializer.save(product=product)

        product = Product.objects.select_related("category").prefetch_related("images", "variants").get(pk=product.pk)

        return success_response(
            "Product created successfully.",
            ProductDetailSerializer(product).data,
            status.HTTP_201_CREATED,
        )


class ProductDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsStaffUser()]

    def get_object(self, slug, request):
        queryset = Product.objects.select_related("category").prefetch_related("images", "variants")
        if request.method == "GET":
            queryset = queryset.filter(is_active=True)
        return get_object_or_404(queryset, slug=slug)

    def get(self, request, slug):
        product = self.get_object(slug, request)
        return success_response("Product retrieved successfully.", ProductDetailSerializer(product).data)

    def patch(self, request, slug):
        product = self.get_object(slug, request)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        product = serializer.save()
        return success_response("Product updated successfully.", ProductDetailSerializer(product).data)

    def delete(self, request, slug):
        product = self.get_object(slug, request)
        product.is_active = False
        product.save()
        return success_response("Product deactivated successfully.")


class ProductImageUploadView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)

        serializer = ProductImageSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        image = serializer.save(product=product)
        return success_response(
            "Image uploaded successfully.",
            ProductImageSerializer(image).data,
            status.HTTP_201_CREATED,
        )


class FeaturedProductsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Product.objects.filter(is_active=True, is_featured=True).select_related(
            "category"
        ).prefetch_related("images", "variants")[:20]

        return success_response(
            "Featured products retrieved successfully.",
            ProductListSerializer(queryset, many=True).data,
        )


class InventoryAdjustView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        product_id = request.data.get("product_id")
        variant_id = request.data.get("variant_id")
        quantity = request.data.get("quantity")
        transaction_type = request.data.get("transaction_type")
        reference = request.data.get("reference", "")
        note = request.data.get("note", "")

        if transaction_type not in dict(TRANSACTION_TYPE_CHOICES):
            return error_response("Validation failed.", {"transaction_type": ["Invalid transaction type."]})

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return error_response("Validation failed.", {"quantity": ["Must be an integer."]})

        if not product_id and not variant_id:
            return error_response(
                "Validation failed.", {"product_id": ["Provide either product_id or variant_id."]}
            )

        with transaction.atomic():
            if variant_id:
                variant = get_object_or_404(ProductVariant.objects.select_for_update(), pk=variant_id)
                previous_stock = variant.stock_quantity
                new_stock = previous_stock + quantity

                if new_stock < 0:
                    return error_response("Insufficient stock for this operation.")

                variant.stock_quantity = new_stock
                variant.save(update_fields=["stock_quantity", "updated_at"])

                InventoryTransaction.objects.create(
                    product=variant.product,
                    variant=variant,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    reference=reference,
                    note=note,
                    created_by=request.user,
                )
                response_data = {"product_id": variant.product_id, "variant_id": variant.id}
            else:
                product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
                previous_stock = product.stock_quantity
                new_stock = previous_stock + quantity

                if new_stock < 0:
                    return error_response("Insufficient stock for this operation.")

                product.stock_quantity = new_stock
                product.save(update_fields=["stock_quantity", "updated_at"])

                InventoryTransaction.objects.create(
                    product=product,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    reference=reference,
                    note=note,
                    created_by=request.user,
                )
                response_data = {"product_id": product.id, "variant_id": None}

        response_data.update({
            "previous_stock": previous_stock,
            "quantity": quantity,
            "new_stock": new_stock,
            "transaction_type": transaction_type,
            "reference": reference,
        })

        return success_response("Inventory updated successfully.", response_data)
