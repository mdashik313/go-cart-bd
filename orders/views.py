from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.pagination import DefaultPagination
from core.permissions import IsStaffUser
from core.response import error_response, success_response
from payments.services import settle_cod_on_delivery

from .models import ORDER_STATUS_CHOICES, Order
from .serializers import OrderDetailSerializer, OrderListSerializer
from .services import CheckoutError, cancel_order, create_order_from_cart, update_order_status


class CheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not (request.user and request.user.is_authenticated):
            return error_response(
                "Please login or create an account before placing an order.", status_code=401
            )

        shipping_address_id = request.data.get("shipping_address_id")
        billing_address_id = request.data.get("billing_address_id", shipping_address_id)
        customer_note = request.data.get("customer_note", "")

        if not shipping_address_id:
            return error_response("Validation failed.", {"shipping_address_id": ["This field is required."]})

        try:
            order = create_order_from_cart(request.user, shipping_address_id, billing_address_id, customer_note)
        except CheckoutError as exc:
            return error_response(exc.message, exc.errors)

        return success_response(
            "Order created successfully.", OrderDetailSerializer(order).data, status.HTTP_201_CREATED
        )


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Order.objects.filter(customer=request.user)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderListSerializer(page, many=True)

        return success_response("Orders retrieved successfully.", {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
        })


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"), order_number=order_number, customer=request.user
        )
        return success_response("Order retrieved successfully.", OrderDetailSerializer(order).data)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, customer=request.user)

        try:
            order, changed = cancel_order(order)
        except CheckoutError as exc:
            return error_response(exc.message)

        message = "Order cancelled successfully." if changed else "Order is already cancelled."
        return success_response(message, OrderDetailSerializer(order).data)


class AdminOrderListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        queryset = Order.objects.select_related("customer").all()

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        payment_status_filter = request.query_params.get("payment_status")
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)

        order_number = request.query_params.get("order_number")
        if order_number:
            queryset = queryset.filter(order_number__icontains=order_number)

        customer_email = request.query_params.get("customer")
        if customer_email:
            queryset = queryset.filter(customer__email__icontains=customer_email)

        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderListSerializer(page, many=True)

        return success_response("Orders retrieved successfully.", {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
        })


class AdminOrderDetailView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request, order_number):
        order = get_object_or_404(Order.objects.prefetch_related("items"), order_number=order_number)
        return success_response("Order retrieved successfully.", OrderDetailSerializer(order).data)


class AdminOrderStatusView(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)
        new_status = request.data.get("status")

        if new_status not in dict(ORDER_STATUS_CHOICES):
            return error_response("Validation failed.", {"status": ["Invalid status."]})

        try:
            if new_status == "CANCELLED":
                order, _ = cancel_order(order)
            else:
                order = update_order_status(order, new_status)
                if new_status == "DELIVERED":
                    settle_cod_on_delivery(order)
                    order.refresh_from_db()
        except CheckoutError as exc:
            return error_response(exc.message)

        return success_response("Order status updated successfully.", OrderDetailSerializer(order).data)
