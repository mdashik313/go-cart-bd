from decimal import ROUND_DOWN

from django.utils.text import slugify


def generate_unique_slug(model, name, instance=None):
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    queryset = model.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def calculate_discount_percentage(price, compare_at_price):
    if not compare_at_price or compare_at_price <= price:
        return None
    discount = (compare_at_price - price) * 100 / compare_at_price
    return int(discount.to_integral_value(rounding=ROUND_DOWN))


def get_stock_status(quantity, low_stock_threshold):
    if quantity <= 0:
        return "OUT_OF_STOCK"
    if quantity <= low_stock_threshold:
        return "LOW_STOCK"
    return "IN_STOCK"
