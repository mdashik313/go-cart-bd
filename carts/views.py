from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.response import error_response, success_response
from products.models import Product, ProductVariant

from .models import CartItem
from .services import (
    InsufficientStockError,
    add_item_to_cart,
    get_available_stock,
    get_current_cart,
    get_unit_price,
    merge_guest_cart_into_user_cart,
    serialize_cart,
)


class CartDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart, _ = get_current_cart(request)
        return success_response("Cart retrieved successfully.", serialize_cart(cart))


class CartItemListCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        product_id = request.data.get("product_id")
        variant_id = request.data.get("variant_id")
        quantity = request.data.get("quantity")

        if not product_id:
            return error_response("Validation failed.", {"product_id": ["This field is required."]})

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return error_response("Validation failed.", {"quantity": ["Must be a positive integer."]})

        if quantity <= 0:
            return error_response("Validation failed.", {"quantity": ["Quantity must be greater than zero."]})

        product = Product.objects.filter(pk=product_id, is_active=True).first()
        if not product:
            return error_response("Validation failed.", {"product_id": ["Product not found or unavailable."]})

        variant = None
        if variant_id:
            variant = ProductVariant.objects.filter(pk=variant_id, product=product, is_active=True).first()
            if not variant:
                return error_response("Validation failed.", {"variant_id": ["Variant not found for this product."]})
        elif product.variants.exists():
            return error_response(
                "Validation failed.", {"variant_id": ["This product requires selecting a variant."]}
            )

        cart, _ = get_current_cart(request)

        try:
            item = add_item_to_cart(cart, product, variant, quantity)
        except InsufficientStockError as exc:
            return error_response(
                "Insufficient stock for the requested quantity.",
                {"quantity": [f"Only {exc.available} in stock."]},
            )

        unit_price = get_unit_price(product, variant)
        data = {
            "item_id": item.id,
            "product_id": product.id,
            "variant_id": variant.id if variant else None,
            "quantity": item.quantity,
            "unit_price": str(unit_price),
            "subtotal": str(unit_price * item.quantity),
        }
        if cart.guest_token:
            data["cart_token"] = cart.guest_token

        return success_response("Product added to cart successfully.", data, status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get_item(self, request, item_id):
        cart, _ = get_current_cart(request)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        return cart, item

    def patch(self, request, item_id):
        cart, item = self.get_item(request, item_id)

        try:
            quantity = int(request.data.get("quantity"))
        except (TypeError, ValueError):
            return error_response("Validation failed.", {"quantity": ["Must be a positive integer."]})

        if quantity <= 0:
            return error_response(
                "Validation failed.",
                {"quantity": ["Quantity must be greater than zero. Use DELETE to remove the item."]},
            )

        available = get_available_stock(item.product, item.variant)
        if quantity > available:
            return error_response(
                "Insufficient stock for the requested quantity.",
                {"quantity": [f"Only {available} in stock."]},
            )

        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])

        unit_price = get_unit_price(item.product, item.variant)
        data = {
            "item_id": item.id,
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity,
            "unit_price": str(unit_price),
            "subtotal": str(unit_price * item.quantity),
        }
        if cart.guest_token:
            data["cart_token"] = cart.guest_token

        return success_response("Cart item updated successfully.", data)

    def delete(self, request, item_id):
        cart, item = self.get_item(request, item_id)
        item.delete()

        data = serialize_cart(cart)
        if cart.guest_token:
            data["cart_token"] = cart.guest_token

        return success_response("Item removed from cart successfully.", data)


class CartClearView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart, _ = get_current_cart(request)
        cart.items.all().delete()

        data = serialize_cart(cart)
        if cart.guest_token:
            data["cart_token"] = cart.guest_token

        return success_response("Cart cleared successfully.", data)


class CartMergeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        guest_token = request.headers.get("X-Cart-Token")
        if not guest_token:
            return error_response(
                "Validation failed.", {"cart_token": ["X-Cart-Token header is required to merge a cart."]}
            )

        cart, adjustments = merge_guest_cart_into_user_cart(guest_token, request.user)

        data = serialize_cart(cart)
        data["merge_adjustments"] = adjustments

        return success_response("Cart merged successfully.", data)
