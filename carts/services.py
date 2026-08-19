import secrets
from decimal import Decimal

from django.db import transaction

from .models import Cart, CartItem


class InsufficientStockError(Exception):
    def __init__(self, available):
        self.available = available
        super().__init__(f"Only {available} in stock.")


def generate_guest_token():
    return secrets.token_urlsafe(32)


def get_current_cart(request):
    """
      - authenticated -> the user's cart 
      - guest with a valid X-Cart-Token -> return guest cart
      - guest with no/invalid token -> a new guest cart

    Returns (cart, guest_token). guest_token is None for authenticated users.
    """
    if request.user and request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart, None

    token = request.headers.get("X-Cart-Token")
    if token:
        cart = Cart.objects.filter(guest_token=token).first()
        if cart:
            return cart, token

    new_token = generate_guest_token()
    cart = Cart.objects.create(guest_token=new_token)
    return cart, new_token


def get_available_stock(product, variant):
    if variant:
        return variant.stock_quantity if variant.is_active else 0
    if product.variants.exists():
        # Product with variants only sells through its variants.
        return 0
    return product.stock_quantity


def get_unit_price(product, variant):
    return variant.price if variant else product.price


def add_item_to_cart(cart, product, variant, quantity):
    """Adding or increasing the quantity of a cart item."""
    existing = CartItem.objects.filter(cart=cart, product=product, variant=variant).first()
    current_qty = existing.quantity if existing else 0
    new_qty = current_qty + quantity

    available = get_available_stock(product, variant)
    if new_qty > available:
        raise InsufficientStockError(available)

    if existing:
        existing.quantity = new_qty
        existing.save(update_fields=["quantity", "updated_at"])
        return existing

    return CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=new_qty)


def _primary_image_url(product):
    images = list(product.images.all())
    if not images:
        return None
    primary = next((image for image in images if image.is_primary), images[0])
    return primary.image.url if primary.image else None


def _variant_data(variant):
    if not variant:
        return None
    return {"id": variant.id, "sku": variant.sku, "attributes": variant.attributes}


def calculate_cart_totals(cart):
    """Centralized cart pricing. Always re-derives prices from the DB, never trusts stored values."""
    items = cart.items.select_related("product", "variant").prefetch_related("product__images")

    subtotal = Decimal("0.00")
    item_count = 0
    item_data = []

    for item in items:
        unit_price = get_unit_price(item.product, item.variant)
        item_subtotal = unit_price * item.quantity
        subtotal += item_subtotal
        item_count += item.quantity

        item_data.append({
            "id": item.id,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "slug": item.product.slug,
                "image": _primary_image_url(item.product),
            },
            "variant": _variant_data(item.variant),
            "quantity": item.quantity,
            "unit_price": str(unit_price),
            "subtotal": str(item_subtotal),
        })

    discount = Decimal("0.00")
    delivery_charge = Decimal("0.00")
    total = subtotal - discount + delivery_charge

    return {
        "items": item_data,
        "subtotal": str(subtotal),
        "discount": str(discount),
        "delivery_charge": str(delivery_charge),
        "total": str(total),
        "item_count": item_count,
    }


def serialize_cart(cart):
    totals = calculate_cart_totals(cart)
    return {
        "cart_type": "USER" if cart.user_id else "GUEST",
        "items": totals["items"],
        "subtotal": totals["subtotal"],
        "discount": totals["discount"],
        "delivery_charge": totals["delivery_charge"],
        "total": totals["total"],
        "item_count": totals["item_count"],
    }

"""Represents one atomic business operation."""
@transaction.atomic
def merge_guest_cart_into_user_cart(guest_token, user):
    """
    The single source of truth for merging a guest cart into a user's cart.
    Used by register, login, and the explicit /api/cart/merge/ endpoint so
    all three behave identically.

    Returns (user_cart, merge_adjustments).
    """
    adjustments = []
    user_cart, _ = Cart.objects.get_or_create(user=user)

    guest_cart = Cart.objects.filter(guest_token=guest_token).first() if guest_token else None
    if not guest_cart or guest_cart.pk == user_cart.pk:
        return user_cart, adjustments

    for guest_item in guest_cart.items.select_related("product", "variant"):
        available = get_available_stock(guest_item.product, guest_item.variant)

        existing_item = CartItem.objects.filter(
            cart=user_cart, product=guest_item.product, variant=guest_item.variant
        ).first()
        existing_qty = existing_item.quantity if existing_item else 0
        requested_qty = existing_qty + guest_item.quantity
        final_qty = min(requested_qty, available)

        if final_qty != requested_qty:
            adjustments.append({
                "product_id": guest_item.product_id,
                "variant_id": guest_item.variant_id,
                "requested_quantity": requested_qty,
                "available_quantity": available,
                "final_quantity": final_qty,
                "reason": "Quantity reduced because of available stock.",
            })

        if final_qty <= 0:
            if existing_item:
                existing_item.delete()
            continue

        if existing_item:
            existing_item.quantity = final_qty
            existing_item.save(update_fields=["quantity", "updated_at"])
        else:
            CartItem.objects.create(
                cart=user_cart, product=guest_item.product, variant=guest_item.variant, quantity=final_qty
            )

    guest_cart.items.all().delete()
    guest_cart.delete()

    return user_cart, adjustments
