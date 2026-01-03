# products/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework import status
import traceback

from productmanagement.models import Product, ProductCategory
from productmanagement.serializers import (
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductDetailSerializer,
    ProductCategorySerializer,
)

class IsAdminUserCustom(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

class ProductCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProductCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            try:
                product = serializer.save()
                responseData = {
                    "statuscode": status.HTTP_201_CREATED,
                    "message": "Product created successfully",
                    "data": ProductDetailSerializer(product).data,
                }
                return Response(responseData, status=status.HTTP_201_CREATED)
            except Exception as e:
                traceback.print_exc()
                responseData = {
                    "statuscode": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                }
                return Response(responseData, status=status.HTTP_400_BAD_REQUEST)

class ProductUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            responseData = {
                "statuscode": status.HTTP_404_NOT_FOUND,
                "message": "Product not found",
            }
            return Response(responseData, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductUpdateSerializer(
            product,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
                responseData = {
                    "statuscode": status.HTTP_200_OK,
                    "message": "Product updated successfully",
                    "data": ProductDetailSerializer(product).data,
                }
                return Response(responseData, status=status.HTTP_200_OK)
            except Exception as e:
                traceback.print_exc()
                responseData = {
                    "statuscode": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                }
                return Response(responseData, status=status.HTTP_400_BAD_REQUEST)

class ProductDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            product.delete()
            responseData = {
                "statuscode": status.HTTP_204_NO_CONTENT,
                "message": "Product deleted successfully",
            }
            return Response(responseData, status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist:
            responseData = {
                "statuscode": status.HTTP_404_NOT_FOUND,
                "message": "Product not found",
            }
            return Response(responseData, status=status.HTTP_404_NOT_FOUND)

class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, is_active=True)
            responseData = {
                "statuscode": status.HTTP_200_OK,
                "data": ProductDetailSerializer(product).data,
            }
            return Response(responseData, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            responseData = {
                "statuscode": status.HTTP_404_NOT_FOUND,
                "message": "Product not found",
            }
            return Response(responseData, status=status.HTTP_404_NOT_FOUND)


class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.filter(is_active=True)
        serializer = ProductDetailSerializer(products, many=True)
        responseData = {
            "statuscode": status.HTTP_200_OK,
            "data": serializer.data,
        }
        return Response(responseData, status=status.HTTP_200_OK)


class CategoryCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def post(self, request):
        serializer = ProductCategorySerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                category = serializer.save()
                responseData = {
                    "statuscode": status.HTTP_201_CREATED,
                    "message": "Category created successfully",
                    "data": ProductCategorySerializer(category).data,
                }
                return Response(responseData, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                traceback.print_exc()
                return Response(
                    {"statuscode": 400, "message": str(e)},
                    status=400,
                )


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = ProductCategory.objects.filter(is_active=True)
        return Response(
            {
                "statuscode": 200,
                "data": ProductCategorySerializer(categories, many=True).data,
            },
            status=200,
        )