from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

TRANSACTION_TYPE_CHOICES = (
    ("RESTOCK", "Restock"),
    ("SALE", "Sale"),
    ("ADJUSTMENT", "Adjustment"),
    ("RETURN", "Return"),
    ("CANCELLATION", "Cancellation"),
)


class Category(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    sku = models.CharField(max_length=100, unique=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )

    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["price"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_gte_0"),
            models.CheckConstraint(condition=models.Q(stock_quantity__gte=0), name="product_stock_gte_0"),
            models.CheckConstraint(
                condition=models.Q(compare_at_price__isnull=True) | models.Q(compare_at_price__gte=models.F("price")),
                name="product_compare_at_price_gte_price",
            ),
        ]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_images"
        ordering = ["-is_primary", "sort_order", "id"]

    def __str__(self):
        return f"{self.product.name} image"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(
                is_primary=False
            )


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock_quantity = models.PositiveIntegerField(default=0)
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_variants"
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["product", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="variant_price_gte_0"),
            models.CheckConstraint(condition=models.Q(stock_quantity__gte=0), name="variant_stock_gte_0"),
        ]

    def __str__(self):
        return self.sku


class InventoryTransaction(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="inventory_transactions", null=True, blank=True
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="inventory_transactions", null=True, blank=True
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    quantity = models.IntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_transactions"
        indexes = [
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.quantity}"
