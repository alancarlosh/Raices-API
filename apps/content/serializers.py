from rest_framework import serializers

from .models import Escena, ObjetoInteractivo


class ObjetoInteractivoSerializer(serializers.ModelSerializer):
    teclado = serializers.SerializerMethodField()

    class Meta:
        model = ObjetoInteractivo
        fields = ["id", "palabra", "glosa_es", "teclado", "sprite_key",
                  "audio_ogg", "audio_m4a", "x", "y", "width", "height"]
        read_only_fields = fields

    def get_teclado(self, obj) -> str:
        """Con qué alfabeto se escribe ESTA palabra: "totonaco" o "espanol".

        POR QUÉ EXISTE. El ejercicio de escritura valida contra `palabra`,
        y mientras no llegue el vocabulario real `palabra` contiene el
        mismo placeholder en español que `glosa_es` (ver el help_text del
        modelo). Con un teclado totonaco —23 letras, sin b c d f g v z ni
        tildes— eso hace el ejercicio literalmente IMPOSIBLE: medido el
        2026-11-09, 56 de las 87 palabras del catálogo (64%) no se podían
        teclear. Los alumnos del laboratorio lo reportaron ese mismo día
        como "no está la h", "no está la f", "falta la c"... y tenían
        razón, aunque creyeran que el fallo era del teclado.

        La regla es la que el propio modelo documenta: si `palabra` es
        igual a `glosa_es`, es el placeholder español y se escribe con
        teclado español. En cuanto una fila reciba su palabra totonaca
        real, ESA fila pasa sola al teclado totonaco, sin desplegar nada
        ni deshacer nada.

        Va en el servidor y no en el cliente a propósito: qué significa
        "esta fila todavía es un placeholder" es semántica del catálogo.
        Si mañana se marca de otra forma —un campo propio, un estado— se
        cambia aquí y los clientes no se enteran.
        """
        es_placeholder = obj.palabra.strip().casefold() == obj.glosa_es.strip().casefold()
        return "espanol" if (es_placeholder and obj.glosa_es.strip()) else "totonaco"


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
