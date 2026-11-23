from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login por correo, no por username.

    `username_field` es el nombre que TokenObtainSerializer._init_ usa para
    (a) crear el campo del body y (b) construir el kwarg con el que llama a
    `authenticate()` -- fijarlo en "email" basta para las dos cosas a la
    vez, SIN reescribir `validate()`: `authenticate(email=..., password=...)`
    llega tal cual a EmailBackend (ver backends.py y AUTHENTICATION_BACKENDS
    en settings.py), que es quien de verdad sabe convertir un correo en una
    cuenta. USERNAME_FIELD del modelo (Usuario.USERNAME_FIELD) sigue siendo
    "username" -- esto vive un nivel por encima, solo en esta vista.
    """

    username_field = "email"


class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return value

    def validate_email(self, value):
        # Requerido y único: tanto la recuperación de contraseña como el
        # login (EmailTokenObtainPairSerializer/EmailBackend) buscan la
        # cuenta por email, así que dos cuentas con el mismo correo dejarían
        # ambigua a cuál pertenece un intento de login o un restablecimiento.
        #
        # SE GUARDA EN MINÚSCULAS, y no solo se compara así: EmailBackend
        # autentica con `email__iexact` (un correo no debería depender de
        # cómo se tecleó), pero la unicidad de la BASE DE DATOS (ver
        # Usuario.email) es sensible a mayúsculas -- sin normalizar aquí,
        # "Ana@x.com" y "ana@x.com" podrían registrarse como DOS cuentas
        # distintas que la base permite pero que el login ya no podría
        # distinguir (MultipleObjectsReturned), dejando a las dos sin poder
        # entrar.
        value = value.lower()
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese correo.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "email", "rol", "email_verificado"]
        read_only_fields = fields


class SolicitarResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmarVerificacionEmailSerializer(serializers.Serializer):
    # Largo fijo: un codigo de 6 digitos que no mida 6 ya es invalido, y
    # decirlo en el propio serializer evita gastar una llamada al
    # servicio (y una fila de la tabla) en algo que nunca va a coincidir.
    codigo = serializers.CharField(min_length=6, max_length=6)


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
