from rest_framework import serializers
from productmanagement.models import Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "description"]

class AdminValidationMixin:
    def validate(self, attrs):
        request = self.context.get("request")
        if not request.user.is_authenticated or not request.user.is_admin:
            raise serializers.ValidationError(
                {
                    "message": "Only admin users can perform this action",
                    "statuscode": 403,
                }
            )
        return attrs
    
class ProductCreateSerializer(AdminValidationMixin, serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock", "is_active", "category"]
        # Making fields required
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': True},
            'price': {'required': True}
        }

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return Product.objects.create(
            created_by=request.user,
            **validated_data
        )
    
class ProductUpdateSerializer(AdminValidationMixin, serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock", "is_active"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value


class ProductDetailSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "stock",
            "is_active",
            "created_by",
            "created_at",
            "category",
        ]


