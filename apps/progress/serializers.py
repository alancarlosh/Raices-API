from rest_framework import serializers

from .models import IntentoEscritura


class IntentoEscrituraInputSerializer(serializers.Serializer):
    texto_ingresado = serializers.CharField(max_length=150, allow_blank=False)


class IntentoEscrituraResultSerializer(serializers.ModelSerializer):
    correcto = serializers.BooleanField(read_only=True)

    class Meta:
        model = IntentoEscritura
        fields = ["id", "texto_ingresado", "correcto", "creado_en"]
        read_only_fields = fields


class ProgresoEscenaSerializer(serializers.Serializer):
    escena_id = serializers.IntegerField()
    escena_nombre = serializers.CharField()
    lengua = serializers.CharField()
    total_objetos = serializers.IntegerField()
    objetos_descubiertos = serializers.IntegerField()
    porcentaje = serializers.FloatField()
    objetos_dominados = serializers.IntegerField()
    porcentaje_dominado = serializers.FloatField()


class ProgresoTotalSerializer(serializers.Serializer):
    total_objetos = serializers.IntegerField()
    objetos_descubiertos = serializers.IntegerField()
    porcentaje = serializers.FloatField()
    objetos_dominados = serializers.IntegerField()
    porcentaje_dominado = serializers.FloatField()


class ProgresoResponseSerializer(serializers.Serializer):
    escenas = ProgresoEscenaSerializer(many=True)
    total = ProgresoTotalSerializer()
