from rest_framework import serializers

from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    payment_id = serializers.IntegerField(source="id", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "payment_id", "order_number", "transaction_id", "provider", "payment_method",
            "amount", "currency", "status", "paid_at", "created_at",
        ]


class RefundSerializer(serializers.ModelSerializer):
    refund_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Refund
        fields = ["refund_id", "payment", "amount", "reason", "status", "provider_refund_id", "created_at"]
