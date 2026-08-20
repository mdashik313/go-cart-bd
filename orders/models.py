from decimal import Decimal

from django.conf import settings
from django.db import models

ORDER_STATUS_CHOICES = (
    ("PENDING", "Pending"),
    ("CONFIRMED", "Confirmed"),
    ("PROCESSING", "Processing"),
    ("SHIPPED", "Shipped"),
    ("DELIVERED", "Delivered"),
    ("CANCELLED", "Cancelled"),
)

PAYMENT_STATUS_CHOICES = (
    ("UNPAID", "Unpaid"),
    ("PENDING", "Pending"),
    ("PAID", "Paid"),
    ("FAILED", "Failed"),
    ("REFUNDED", "Refunded"),
)


class Order(models.Model):
    order_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="PENDING")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="UNPAID")

    shipping_address_snapshot = models.JSONField()
    billing_address_snapshot = models.JSONField()

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    delivery_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2)

    customer_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )

    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
