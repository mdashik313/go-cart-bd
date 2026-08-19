from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from carts.services import merge_guest_cart_into_user_cart, serialize_cart
from core.response import error_response, success_response

from .models import Address
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        cart, adjustments = merge_guest_cart_into_user_cart(request.headers.get("X-Cart-Token"), user)
        cart_data = serialize_cart(cart)
        if adjustments:
            cart_data["merge_adjustments"] = adjustments

        return success_response(
            "Account created successfully.",
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "cart": cart_data,
            },
            status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        cart, adjustments = merge_guest_cart_into_user_cart(request.headers.get("X-Cart-Token"), user)
        cart_data = serialize_cart(cart)
        if adjustments:
            cart_data["merge_adjustments"] = adjustments

        return success_response("Login successful.", {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "cart": cart_data,
        })


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response("Validation failed.", {"refresh": ["This field is required."]})

        try:
            refresh = RefreshToken(refresh_token)
        except TokenError as exc:
            return error_response("Invalid or expired refresh token.", {"refresh": [str(exc)]}, 401)

        return success_response("Token refreshed successfully.", {"access": str(refresh.access_token)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response("Profile retrieved successfully.", UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()

        return success_response("Password changed successfully.")


class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = request.user.addresses.all()
        return success_response("Addresses retrieved successfully.", AddressSerializer(addresses, many=True).data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        is_default = serializer.validated_data.get("is_default", False)
        if not request.user.addresses.exists():
            is_default = True

        if is_default:
            request.user.addresses.filter(is_default=True).update(is_default=False)

        address = serializer.save(user=request.user, is_default=is_default)

        return success_response(
            "Address created successfully.",
            AddressSerializer(address).data,
            status.HTTP_201_CREATED,
        )


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(Address, pk=pk, user=request.user)

    def get(self, request, pk):
        address = self.get_object(request, pk)
        return success_response("Address retrieved successfully.", AddressSerializer(address).data)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        address = self.get_object(request, pk)
        serializer = AddressSerializer(address, data=request.data, partial=partial)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)

        if serializer.validated_data.get("is_default"):
            request.user.addresses.exclude(pk=address.pk).filter(is_default=True).update(is_default=False)

        serializer.save()
        return success_response("Address updated successfully.", serializer.data)

    def delete(self, request, pk):
        address = self.get_object(request, pk)
        was_default = address.is_default
        address.delete()

        if was_default:
            next_address = request.user.addresses.order_by("-created_at").first()
            if next_address:
                next_address.is_default = True
                next_address.save()

        return success_response("Address deleted successfully.")


class AddressSetDefaultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        request.user.addresses.exclude(pk=address.pk).filter(is_default=True).update(is_default=False)
        address.is_default = True
        address.save()

        return success_response("Default address updated successfully.", AddressSerializer(address).data)
