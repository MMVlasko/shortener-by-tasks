from .serializers import (
    LoginSerializer, RegisterSerializer,
    UserSerializer, ErrorSerializer
)

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from drf_spectacular.utils import extend_schema


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: UserSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer
        },
        description='Аутентификация и создание сессии'
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        login(request, user)

        return Response(UserSerializer(user).data)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: UserSerializer,
            400: ErrorSerializer
        },
        description='Регистрация нового пользователя'
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        login(request, user)

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: {'type': 'object', 'properties': {'message': {'type': 'string'}}},
            401: ErrorSerializer
        },
        description='Выход из системы (удаление сессии)'
    )
    def post(self, request):
        logout(request)
        return Response({'message': 'Успешный выход'})