from django.contrib import admin

from .models import Payment, Refund


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "order", "payment_method", "provider", "amount", "status", "created_at"]
    list_filter = ["status", "payment_method", "provider"]
    search_fields = ["transaction_id", "provider_transaction_id", "order__order_number"]
    inlines = [RefundInline]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["payment", "amount", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["payment__transaction_id", "provider_refund_id"]
