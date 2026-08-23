from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Payment, Refund
from .providers import get_payment_provider


class PaymentError(Exception):
    def __init__(self, message, errors=None):
        self.message = message
        self.errors = errors or {}
        super().__init__(message)


def generate_transaction_id():
    today_str = timezone.now().strftime("%Y%m%d")
    prefix = f"TXN-{today_str}-"
    last_payment = Payment.objects.filter(transaction_id__startswith=prefix).order_by("-transaction_id").first()
    last_seq = int(last_payment.transaction_id.split("-")[-1]) if last_payment else 0
    return f"{prefix}{last_seq + 1:06d}"


@transaction.atomic
def initiate_payment(order, payment_method):
    if order.status != "PENDING":
        raise PaymentError(f"Order is not eligible for payment while in status {order.status}.")

    if order.payment_status == "PAID":
        raise PaymentError("This order has already been paid.")

    payment = Payment.objects.create(
        order=order,
        payment_method=payment_method,
        provider="COD" if payment_method == "COD" else "MOCK",
        transaction_id=generate_transaction_id(),
        amount=order.total,
        currency="BDT",
        status="UNPAID" if payment_method == "COD" else "PENDING",
    )

    if payment_method == "COD":
        # No online payment required — the order can be confirmed immediately.
        order.status = "CONFIRMED"
        order.save(update_fields=["status", "updated_at"])
        return payment

    provider = get_payment_provider(payment.provider)
    result = provider.initiate_payment(payment)

    payment.provider_transaction_id = result.get("provider_transaction_id")
    payment.status = result.get("status", "PROCESSING")
    payment.save(update_fields=["provider_transaction_id", "status", "updated_at"])

    return payment


def verify_webhook_signature(request):
    """
    Demo for a real gateway's signature check
    """
    secret = request.headers.get("X-Webhook-Secret")
    return bool(secret) and secret == settings.PAYMENT_WEBHOOK_SECRET  # check if secret existn and matches the original


@transaction.atomic
def process_webhook(data):
    transaction_id = data.get("transaction_id")
    payment = Payment.objects.select_for_update().filter(transaction_id=transaction_id).first()
    if not payment:
        raise PaymentError("Payment not found for this transaction.")

    if data.get("provider") != payment.provider:
        raise PaymentError("Provider mismatch.")

    incoming_provider_txn_id = data.get("provider_transaction_id")
    if payment.provider_transaction_id and incoming_provider_txn_id != payment.provider_transaction_id:
        raise PaymentError("Provider transaction ID mismatch.")

    try:
        incoming_amount = Decimal(str(data.get("amount")))
    except Exception:
        raise PaymentError("Invalid amount.")

    if incoming_amount != payment.amount:
        raise PaymentError("Amount mismatch.")

    if data.get("currency") != payment.currency:
        raise PaymentError("Currency mismatch.")

    # once a payment reaches a terminal state, further webhooks for
    # the same transaction are accepted but change nothing.
    if payment.status in ("PAID", "REFUND_PENDING", "REFUNDED"):
        return payment, False

    new_status = data.get("status")
    order = payment.order

    if new_status == "PAID":
        payment.status = "PAID"
        payment.paid_at = timezone.now()
        if incoming_provider_txn_id:
            payment.provider_transaction_id = incoming_provider_txn_id
        payment.save(update_fields=["status", "paid_at", "provider_transaction_id", "updated_at"])

        order.payment_status = "PAID"
        if order.status == "PENDING":
            order.status = "CONFIRMED"
        order.save(update_fields=["status", "payment_status", "updated_at"])

    elif new_status == "FAILED":
        payment.status = "FAILED"
        payment.save(update_fields=["status", "updated_at"])

        order.payment_status = "FAILED"
        order.save(update_fields=["payment_status", "updated_at"])

    else:
        raise PaymentError("Unsupported payment status in webhook payload.")

    return payment, True


def get_refundable_amount(payment):
    refunded = payment.refunds.filter(status="COMPLETED").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return payment.amount - refunded


@transaction.atomic
def process_refund(payment, amount, reason=""):
    if payment.status not in ("PAID", "REFUND_PENDING"):
        raise PaymentError("Only paid payments can be refunded.")

    refundable = get_refundable_amount(payment)
    if amount <= 0 or amount > refundable:
        raise PaymentError(f"Refund amount must be between 0 and {refundable}.")

    refund = Refund.objects.create(payment=payment, amount=amount, reason=reason, status="PENDING")

    provider = get_payment_provider(payment.provider)
    result = provider.refund_payment(payment, amount)

    refund.status = result.get("status", "COMPLETED")
    refund.provider_refund_id = result.get("provider_refund_id")
    refund.save(update_fields=["status", "provider_refund_id", "updated_at"])

    if refund.status == "COMPLETED":
        remaining = get_refundable_amount(payment)
        payment.status = "REFUNDED" if remaining <= 0 else "PAID"
        payment.save(update_fields=["status", "updated_at"])

    return refund


@transaction.atomic
def refund_for_cancelled_order(order):
    """Called from orders.services.cancel_order — never called the other way around."""
    payment = Payment.objects.filter(order=order, status="PAID").order_by("-created_at").first()
    if not payment:
        return None

    payment.status = "REFUND_PENDING"
    payment.save(update_fields=["status", "updated_at"])

    return process_refund(payment, get_refundable_amount(payment), reason="Order cancelled")


def settle_cod_on_delivery(order):
    """triggers when an order is marked DELIVERED."""
    if order.payment_status == "PAID":
        return

    cod_payment = Payment.objects.filter(order=order, payment_method="COD").order_by("-created_at").first()
    if not cod_payment:
        return

    cod_payment.status = "PAID"
    cod_payment.paid_at = timezone.now()
    cod_payment.save(update_fields=["status", "paid_at", "updated_at"])

    order.payment_status = "PAID"
    order.save(update_fields=["payment_status", "updated_at"])
