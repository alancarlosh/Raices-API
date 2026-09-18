from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .models import Usuario


class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return value

    def validate_email(self, value):
        # Requerido y único: la recuperación de contraseña busca la cuenta
        # por email, así que dos cuentas con el mismo correo dejarían
        # ambigua a cuál se le restablece la contraseña.
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese correo.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "email", "rol"]
        read_only_fields = fields


class SolicitarResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmarResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            pk = force_str(urlsafe_base64_decode(attrs["uid"]))
            usuario = Usuario.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
            raise serializers.ValidationError({"token": ["Enlace de restablecimiento inválido."]})

        if not default_token_generator.check_token(usuario, attrs["token"]):
            raise serializers.ValidationError({"token": ["Enlace de restablecimiento inválido o expirado."]})

        try:
            password_validation.validate_password(attrs["password"], user=usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})

        attrs["usuario"] = usuario
        return attrs
