from django.contrib.auth import password_validation
from rest_framework import serializers

from .models import Usuario


class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "email", "rol"]
        read_only_fields = fields
