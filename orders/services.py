from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from carts.models import Cart
from payments.services import refund_for_cancelled_order
from products.models import InventoryTransaction, Product, ProductVariant
from users.models import Address

from .models import Order, OrderItem

"""key is the current status, and the value is a set of statuses it is allowed to move to"""
ORDER_STATUS_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "PROCESSING", "CANCELLED"},
    "CONFIRMED": {"PROCESSING", "CANCELLED"},
    "PROCESSING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


class CheckoutError(Exception):
    def __init__(self, message, errors=None):
        self.message = message
        self.errors = errors or {}
        super().__init__(message)


def can_transition_status(current_status, new_status):
    return new_status in ORDER_STATUS_TRANSITIONS.get(current_status, set())


def generate_order_number():
    today_str = timezone.now().strftime("%Y%m%d")
    prefix = f"ORD-{today_str}-"
    last_order = Order.objects.filter(order_number__startswith=prefix).order_by("-order_number").first()
    last_seq = int(last_order.order_number.split("-")[-1]) if last_order else 0
    return f"{prefix}{last_seq + 1:06d}"


def _address_snapshot(address):
    return {
        "full_name": address.full_name,
        "phone": address.phone,
        "address_line": address.address_line,
        "city": address.city,
        "area": address.area,
        "postal_code": address.postal_code,
        "country": address.country,
    }


@transaction.atomic
def create_order_from_cart(user, shipping_address_id, billing_address_id, customer_note=""):
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        raise CheckoutError("Your cart is empty.")

    items = list(cart.items.select_related("product", "variant").all())

    shipping_address = Address.objects.filter(pk=shipping_address_id, user=user).first()
    if not shipping_address:
        raise CheckoutError("Validation failed.", {"shipping_address_id": ["Invalid shipping address."]})

    billing_address = Address.objects.filter(pk=billing_address_id, user=user).first()
    if not billing_address:
        raise CheckoutError("Validation failed.", {"billing_address_id": ["Invalid billing address."]})

    order_items_data = []
    subtotal = Decimal("0.00")

    for item in items:
        if item.variant_id:
            locked_variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            locked_product = locked_variant.product
            available = locked_variant.stock_quantity if locked_variant.is_active else 0
        else:
            locked_product = Product.objects.select_for_update().get(pk=item.product_id)
            locked_variant = None
            available = 0 if locked_product.variants.exists() else locked_product.stock_quantity

        if not locked_product.is_active:
            raise CheckoutError(
                "Validation failed.", {"product": [f"{locked_product.name} is no longer available."]}
            )

        if locked_variant and not locked_variant.is_active:
            raise CheckoutError(
                "Validation failed.",
                {"variant": [f"Selected variant for {locked_product.name} is no longer available."]},
            )

        if item.quantity > available:
            raise CheckoutError(
                "Validation failed.",
                {"stock": [f"Only {available} of {locked_product.name} left in stock."]},
            )

        unit_price = locked_variant.price if locked_variant else locked_product.price
        item_subtotal = unit_price * item.quantity
        subtotal += item_subtotal

        order_items_data.append({
            "product": locked_product,
            "variant": locked_variant,
            "product_name": locked_product.name,
            "sku": locked_variant.sku if locked_variant else locked_product.sku,
            "unit_price": unit_price,
            "quantity": item.quantity,
            "subtotal": item_subtotal,
        })

    discount = Decimal("0.00")
    delivery_charge = Decimal("0.00")
    total = subtotal - discount + delivery_charge

    order = Order.objects.create(
        order_number=generate_order_number(),
        customer=user,
        shipping_address_snapshot=_address_snapshot(shipping_address),
        billing_address_snapshot=_address_snapshot(billing_address),
        subtotal=subtotal,
        discount=discount,
        delivery_charge=delivery_charge,
        total=total,
        customer_note=customer_note,
    )

    for data in order_items_data:
        product = data.pop("product")
        variant = data.pop("variant")
        quantity = data["quantity"]

        OrderItem.objects.create(order=order, product=product, variant=variant, **data)

        if variant:
            previous_stock = variant.stock_quantity
            variant.stock_quantity = previous_stock - quantity
            variant.save(update_fields=["stock_quantity", "updated_at"])
            InventoryTransaction.objects.create(
                product=product, variant=variant, transaction_type="SALE",
                quantity=-quantity, previous_stock=previous_stock, new_stock=variant.stock_quantity,
                reference=order.order_number, note="Order checkout", created_by=user,
            )
        else:
            previous_stock = product.stock_quantity
            product.stock_quantity = previous_stock - quantity
            product.save(update_fields=["stock_quantity", "updated_at"])
            InventoryTransaction.objects.create(
                product=product, transaction_type="SALE",
                quantity=-quantity, previous_stock=previous_stock, new_stock=product.stock_quantity,
                reference=order.order_number, note="Order checkout", created_by=user,
            )

    cart.items.all().delete()

    return order


@transaction.atomic
def cancel_order(order):
    """cancelling an already-cancelled order won't restock inventory"""
    if order.status == "CANCELLED":
        return order, False

    if order.status in ("SHIPPED", "DELIVERED"):
        raise CheckoutError("This order can no longer be cancelled.")

    for item in order.items.all():
        if item.variant_id:
            variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            previous_stock = variant.stock_quantity
            variant.stock_quantity = previous_stock + item.quantity
            variant.save(update_fields=["stock_quantity", "updated_at"])
            InventoryTransaction.objects.create(
                product_id=item.product_id, variant=variant, transaction_type="CANCELLATION",
                quantity=item.quantity, previous_stock=previous_stock, new_stock=variant.stock_quantity,
                reference=order.order_number, note="Order cancelled", created_by=order.customer,
            )
        elif item.product_id:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            previous_stock = product.stock_quantity
            product.stock_quantity = previous_stock + item.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])
            InventoryTransaction.objects.create(
                product=product, transaction_type="CANCELLATION",
                quantity=item.quantity, previous_stock=previous_stock, new_stock=product.stock_quantity,
                reference=order.order_number, note="Order cancelled", created_by=order.customer,
            )

    order.status = "CANCELLED"
    order.save(update_fields=["status", "updated_at"])

    if order.payment_status == "PAID":
        refund = refund_for_cancelled_order(order)
        if refund:
            order.payment_status = refund.payment.status
            order.save(update_fields=["payment_status", "updated_at"])
            
    return order, True


def update_order_status(order, new_status):
    if not can_transition_status(order.status, new_status):
        raise CheckoutError(f"Cannot change status from {order.status} to {new_status}.")

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return order
