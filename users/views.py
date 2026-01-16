from typing import Any

from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, routers, permissions, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import User
from .services import ActivationService

class UserActivationSerializer(serializers.Serializer):
    key = serializers.UUIDField()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "password",
            "role",
        )

    def validate(self, attrs: dict[str, Any]):
        """Change password to make JWT avaliable"""
        attrs["password"] = make_password(attrs["password"])
        return super().validate(attrs=attrs)

class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        elif self.action == "activate":
            return [permissions.AllowAny()]
        else:
            return [permissions.IsAuthenticated()]

    def list(self, request: Request):
        return Response(UserSerializer(request.user).data, status=200)

    def create(self, request: Request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # activation process
        activation_service = ActivationService(
            email=getattr(serializer.instance, "email")
        )
        activation_key = activation_service.create_activation_key()
        activation_service.save_activation_information(
            user_id=getattr(serializer.instance, "id"),
            activation_key=activation_key
        )
        activation_service.send_user_activation_email(activation_key=activation_key)

        return Response(UserSerializer(serializer.instance).data, status=201)

    @action(methods=["POST"], detail=False, name="activate")
    def activate(self, request: Request) -> Response:
        serializer = UserActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activation_service = ActivationService()
        try:
            activation_service.activate_user(
                activation_key=serializer.validated_data["key"]
            )
        except ValueError as error:
            raise ValidationError("Activation link expired") from error

        return Response(data=None, status=204)

    def resend_activation_link(self, email: str) -> None:
        """
        Send user activation link on email
        :param email:
        :return:
        """
        pass


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
