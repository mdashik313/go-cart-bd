from rest_framework.views import APIView
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from rest_framework.response import Response
from rest_framework import status
import traceback
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

# Token generation function
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# Create your views here.

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request): 
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                user = serializer.save()
                tokens = get_tokens_for_user(user)
                responseData = {
                    "statuscode": status.HTTP_201_CREATED,
                    "message": "User Registered Successfully",
                    "tokens": tokens
                }
                return Response(responseData, status=status.HTTP_201_CREATED)
            except Exception as e:
                traceback.print_exc()
                responseData = {
                    "statuscode": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                }
                return Response(responseData, status=status.HTTP_400_BAD_REQUEST)
        else:
            responseData = {
                "statuscode": status.HTTP_400_BAD_REQUEST,
                "message": serializer.errors,
            }
            return Response(responseData, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                user = serializer.validated_data['user']
                tokens = get_tokens_for_user(user)
                responseData = {
                    "statuscode": status.HTTP_200_OK,
                    "message": "User Logged In Successfully",
                    "tokens": tokens
                }
                return Response(responseData, status=status.HTTP_200_OK)
            except Exception as e:
                traceback.print_exc()
                responseData = {
                    "statuscode": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                }
                return Response(responseData, status=status.HTTP_400_BAD_REQUEST)
        else:
            responseData = {
                "statuscode": status.HTTP_400_BAD_REQUEST,
                "message": serializer.errors,
            }
            return Response(responseData, status=status.HTTP_400_BAD_REQUEST)