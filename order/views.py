import traceback
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from order.models import Order
from order.serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
)


class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            try:
                order = serializer.save()
                responseData = {
                    "statuscode": status.HTTP_201_CREATED,
                    "message": "Order created successfully",
                    "data": OrderDetailSerializer(order).data,
                }
                return Response(responseData, status=status.HTTP_201_CREATED)
            except Exception as e:
                traceback.print_exc()
                return Response(
                    {"statuscode": 400, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )


class OrderListView(APIView):
    """
    Returns all orders of logged-in user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        responseData = {
            "statuscode": status.HTTP_200_OK,
            "data": OrderDetailSerializer(orders, many=True).data,
        }
        return Response(responseData, status=status.HTTP_200_OK)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, user=request.user)
            responseData = {
                "statuscode": status.HTTP_200_OK,
                "data": OrderDetailSerializer(order).data,
            }
            return Response(responseData, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response(
                {"statuscode": 404, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
