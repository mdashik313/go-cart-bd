from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.pagination import DefaultPagination
from core.permissions import IsStaffUser
from core.response import error_response, success_response
from orders.models import Order

from .models import PAYMENT_METHOD_CHOICES, Payment
from .serializers import PaymentSerializer
from .services import PaymentError, initiate_payment, process_refund, process_webhook, verify_webhook_signature


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, customer=request.user)

        payment_method = request.data.get("payment_method")
        if payment_method not in dict(PAYMENT_METHOD_CHOICES):
            return error_response("Validation failed.", {"payment_method": ["Invalid payment method."]})

        try:
            payment = initiate_payment(order, payment_method)
        except PaymentError as exc:
            return error_response(exc.message, exc.errors)

        if payment_method == "COD":
            return success_response("Order confirmed successfully.", {
                "order_number": order.order_number,
                "order_status": order.status,
                "payment_method": payment.payment_method,
                "payment_status": order.payment_status,
            })

        return success_response("Payment initiated successfully.", {
            "payment_id": payment.id,
            "order_number": order.order_number,
            "transaction_id": payment.transaction_id,
            "provider": payment.provider,
            "payment_method": payment.payment_method,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
        }, status.HTTP_201_CREATED)


class PaymentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, customer=request.user)
        payments = order.payments.order_by("-created_at")
        return success_response(
            "Payment history retrieved successfully.", PaymentSerializer(payments, many=True).data
        )


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not verify_webhook_signature(request):
            return error_response("Invalid webhook signature.", status_code=401)

        try:
            payment, changed = process_webhook(request.data)
        except PaymentError as exc:
            return error_response(exc.message, exc.errors)

        if not changed:
            return success_response("Webhook already processed.", {
                "payment_id": payment.id,
                "payment_status": payment.status,
                "order_number": payment.order.order_number,
                "order_status": payment.order.status,
            })

        if payment.status == "PAID":
            return success_response("Payment processed successfully.", {
                "payment_id": payment.id,
                "payment_status": payment.status,
                "order_number": payment.order.order_number,
                "order_status": payment.order.status,
            })

        return success_response("Payment failed.", {
            "payment_id": payment.id,
            "payment_status": payment.status,
            "order_number": payment.order.order_number,
            "order_status": payment.order.status,
        })


class AdminPaymentListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        payments = Payment.objects.select_related("order").all().order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            payments = payments.filter(status=status_filter)

        order_number = request.query_params.get("order_number")
        if order_number:
            payments = payments.filter(order__order_number__icontains=order_number)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(payments, request)
        serializer = PaymentSerializer(page, many=True)

        return success_response("Payments retrieved successfully.", {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
        })


class AdminPaymentDetailView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment.objects.select_related("order"), pk=payment_id)
        return success_response("Payment retrieved successfully.", PaymentSerializer(payment).data)


class AdminPaymentRefundView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)

        try:
            amount = Decimal(str(request.data.get("amount")))
        except Exception:
            return error_response("Validation failed.", {"amount": ["Must be a valid decimal amount."]})

        reason = request.data.get("reason", "")

        try:
            refund = process_refund(payment, amount, reason)
        except PaymentError as exc:
            return error_response(exc.message, exc.errors)

        return success_response("Refund processed successfully.", {
            "refund_id": refund.id,
            "payment_id": payment.id,
            "amount": str(refund.amount),
            "status": refund.status,
            "provider_refund_id": refund.provider_refund_id,
        }, status.HTTP_201_CREATED)
