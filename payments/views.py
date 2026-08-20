from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from orders.models import Order
from .models import PAYMENT_METHOD_CHOICES, Payment
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
