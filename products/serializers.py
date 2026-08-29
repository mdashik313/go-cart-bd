from rest_framework import serializers

from core.utils import calculate_discount_percentage, generate_unique_slug, get_stock_status

from .models import Category, Product, ProductImage, ProductVariant


class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description", "image", "parent",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def validate_parent(self, value):
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("A category cannot be its own parent.")

        if value and self.instance:
            node = value
            while node is not None:
                if node.pk == self.instance.pk:
                    raise serializers.ValidationError("Invalid circular parent relationship.")
                node = node.parent

        return value

    def create(self, validated_data):
        validated_data["slug"] = generate_unique_slug(Category, validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = generate_unique_slug(Category, validated_data["name"], instance=instance)
        return super().update(instance, validated_data)


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "sort_order", "is_primary"]


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "price", "stock_quantity", "attributes", "is_active"]


class ProductListSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer(read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "sku", "short_description", "price", "compare_at_price",
            "discount_percentage", "category", "primary_image", "stock_status", "is_featured", "stock_quantity",
        ]

    def get_discount_percentage(self, obj):
        return calculate_discount_percentage(obj.price, obj.compare_at_price)

    def get_primary_image(self, obj):
        images = list(obj.images.all())
        if not images:
            return None
        primary = next((image for image in images if image.is_primary), images[0])
        return primary.image.url if primary.image else None

    def get_stock_status(self, obj):
        variants = list(obj.variants.all())
        if variants:
            quantity = sum(variant.stock_quantity for variant in variants if variant.is_active)
        else:
            quantity = obj.stock_quantity
        return get_stock_status(quantity, obj.low_stock_threshold)


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["description", "images", "variants"]


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "category", "name", "sku", "short_description", "description",
            "price", "compare_at_price", "cost_price", "stock_quantity",
            "low_stock_threshold", "is_active", "is_featured",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        price = attrs.get("price", getattr(self.instance, "price", None))
        compare_at_price = attrs.get("compare_at_price", getattr(self.instance, "compare_at_price", None))

        if compare_at_price is not None and price is not None and compare_at_price < price:
            raise serializers.ValidationError(
                {"compare_at_price": ["compare_at_price cannot be lower than the selling price."]}
            )

        return attrs

    def create(self, validated_data):
        validated_data["slug"] = generate_unique_slug(Product, validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = generate_unique_slug(Product, validated_data["name"], instance=instance)
        return super().update(instance, validated_data)
