from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product_name", "sku", "quantity", "unit_price", "subtotal"]


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["order_number", "status", "payment_status", "total", "created_at"]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = serializers.JSONField(source="shipping_address_snapshot")
    billing_address = serializers.JSONField(source="billing_address_snapshot")

    class Meta:
        model = Order
        fields = [
            "order_number", "status", "payment_status", "items",
            "shipping_address", "billing_address",
            "subtotal", "discount", "delivery_charge", "total",
            "customer_note", "created_at",
        ]
