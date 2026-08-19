from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="cart"
    )
    guest_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(user__isnull=False) & models.Q(guest_token__isnull=True))
                    | (models.Q(user__isnull=True) & models.Q(guest_token__isnull=False))
                ),
                name="cart_owner_xcart",
            ),
        ]

    def __str__(self):
        return f"Cart({self.user or self.guest_token})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="cart_items")
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        constraints = [
            models.UniqueConstraint(fields=["cart", "product", "variant"], name="unique_cart_product_variant"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cart_item_quantity_gt_0"),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
