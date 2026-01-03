from rest_framework import serializers
from django.db import transaction
from order.models import Order, OrderItem
from productmanagement.models import Product


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        try:
            product = Product.objects.get(
                id=attrs["product_id"],
                is_active=True
            )
        except Product.DoesNotExist:
            raise serializers.ValidationError("Invalid product")

        if product.stock < attrs["quantity"]:
            raise serializers.ValidationError(
                f"Insufficient stock for {product.name}"
            )

        attrs["product"] = product
        return attrs


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True)

    def create(self, validated_data):
        user = self.context["request"].user
        items_data = validated_data["items"]

        with transaction.atomic():
            order = Order.objects.create(user=user)
            total_amount = 0

            for item in items_data:
                product = item["product"]
                quantity = item["quantity"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                )

                product.stock -= quantity
                product.save()

                total_amount += product.price * quantity

            order.total_amount = total_amount
            order.save()

        return order


class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_amount",
            "items",
            "created_at",
        ]

    def get_items(self, obj):
        return [
            {
                "product_id": item.product.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": item.price,
            }
            for item in obj.items.all()
        ]
