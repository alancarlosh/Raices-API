from rest_framework import serializers

from .models import MedicionRendimiento

# Mínimo de segundos contados para que una medida valga. Por debajo de
# esto el percentil 5 no significa nada: con 6 muestras el "peor segundo de
# cada veinte" es literalmente el mínimo, y la cifra miente sobre su propia
# precisión. Doce segundos andando dan un p5 que ya separa un tirón real de
# un cuadro suelto.
MUESTRAS_MINIMAS = 12

# Techos de cordura. No son límites de seguridad — el endpoint ya exige
# sesión — sino de CALIDAD DEL DATO: una fila con 3.000 cuadros/s o con 400
# millones de píxeles es un cliente roto o manipulado, y una sola fila así
# arruina cualquier promedio de la tabla sin que se note a simple vista.
FPS_MAX = 240
PIXELES_MAX = 40_000_000
MALLAS_MAX = 200_000


class MedicionRendimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicionRendimiento
        fields = [
            "id", "escena", "fps_p50", "fps_p5", "fps_min", "muestras",
            "dpr", "pixeles", "mallas", "gpu", "navegador", "nucleos",
            "memoria_gb", "creado_en",
        ]
        read_only_fields = ["id", "creado_en"]

    def validate_muestras(self, v):
        if v < MUESTRAS_MINIMAS:
            raise serializers.ValidationError(
                f"hacen falta al menos {MUESTRAS_MINIMAS} segundos contados; "
                f"llegaron {v}"
            )
        return v

    def validate_dpr(self, v):
        if not (0.1 <= v <= 4.0):
            raise serializers.ValidationError("dpr fuera de rango (0.1 a 4.0)")
        return v

    def validate_pixeles(self, v):
        if v > PIXELES_MAX:
            raise serializers.ValidationError("demasiados píxeles por cuadro")
        return v

    def validate_mallas(self, v):
        if v > MALLAS_MAX:
            raise serializers.ValidationError("demasiadas mallas")
        return v

    def validate(self, datos):
        for campo in ("fps_p50", "fps_p5", "fps_min"):
            v = datos.get(campo)
            if v is not None and not (1 <= v <= FPS_MAX):
                raise serializers.ValidationError(
                    {campo: f"cuadros/s fuera de rango (1 a {FPS_MAX})"}
                )
        # EL ORDEN ENTRE LAS TRES CIFRAS ES PARTE DEL DATO. Por definición
        # min <= p5 <= p50; si no se cumple, el cliente no está calculando
        # lo que dice calcular y la fila no es comparable con las demás.
        # Vale la pena rechazarla: una tabla con filas incoherentes es peor
        # que una tabla con menos filas, porque no se distinguen al leer.
        p50, p5, mn = datos.get("fps_p50"), datos.get("fps_p5"), datos.get("fps_min")
        if None not in (p50, p5, mn) and not (mn <= p5 <= p50):
            raise serializers.ValidationError(
                "incoherente: debe cumplirse fps_min <= fps_p5 <= fps_p50 "
                f"(llegaron {mn}, {p5}, {p50})"
            )
        return datos
