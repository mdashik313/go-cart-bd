from django.db import models

PAYMENT_METHOD_CHOICES = (
    ("COD", "Cash on Delivery"),
    ("CARD", "Card"),
    ("MOBILE_BANKING", "Mobile Banking"),
)

PAYMENT_STATUS_CHOICES = (
    ("UNPAID", "Unpaid"),
    ("PENDING", "Pending"),
    ("PROCESSING", "Processing"),
    ("PAID", "Paid"),
    ("FAILED", "Failed"),
    ("REFUND_PENDING", "Refund Pending"),
    ("REFUNDED", "Refunded"),
)

REFUND_STATUS_CHOICES = (
    ("PENDING", "Pending"),
    ("PROCESSING", "Processing"),
    ("COMPLETED", "Completed"),
    ("FAILED", "Failed"),
)


class Payment(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payments")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    provider = models.CharField(max_length=30, default="MOCK")

    transaction_id = models.CharField(max_length=40, unique=True)
    provider_transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="BDT")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="UNPAID")

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_id"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_amount_gte_0"),
        ]

    def __str__(self):
        return self.transaction_id


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default="PENDING")
    provider_refund_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "refunds"
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="refund_amount_gte_0"),
        ]

    def __str__(self):
        return f"Refund {self.amount} for {self.payment.transaction_id}"
