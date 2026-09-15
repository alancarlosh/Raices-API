from rest_framework import serializers

from .models import Escena, ObjetoInteractivo


class ObjetoInteractivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoInteractivo
        fields = ["id", "palabra", "glosa_es", "sprite_key", "audio_ogg", "audio_m4a", "x", "y", "width", "height"]
        read_only_fields = fields


class EscenaSerializer(serializers.ModelSerializer):
    objetos = ObjetoInteractivoSerializer(many=True, read_only=True)
    lengua = serializers.CharField(source="lengua.codigo", read_only=True)

    class Meta:
        model = Escena
        fields = ["id", "codigo", "nombre", "lengua", "fondo", "objetos"]
        read_only_fields = fields


class EscenaListSerializer(serializers.ModelSerializer):
    """Listado ligero para que el frontend arme su grafo de navegación entre cuartos."""

    lengua = serializers.CharField(source="lengua.codigo", read_only=True)

    class Meta:
        model = Escena
        fields = ["id", "codigo", "nombre", "lengua", "orden"]
        read_only_fields = fields
