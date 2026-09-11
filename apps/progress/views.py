from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors, services
from .serializers import (
    IntentoEscrituraInputSerializer,
    IntentoEscrituraResultSerializer,
    ProgresoResponseSerializer,
)


class ObjetoDescubrirView(APIView):
    """POST /api/objetos/<id>/descubrir/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        services.progreso_marcar_descubierto(usuario=request.user, objeto_id=pk)
        return Response({"descubierto": True})


class ObjetoIntentoEscrituraView(APIView):
    """POST /api/objetos/<id>/intento-escritura/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        entrada = IntentoEscrituraInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        intento = services.intento_escritura_registrar(
            usuario=request.user,
            objeto_id=pk,
            texto_ingresado=entrada.validated_data["texto_ingresado"],
        )
        return Response(IntentoEscrituraResultSerializer(intento).data)


class ProgresoResumenView(APIView):
    """GET /api/progreso/ — % descubierto y % dominado, por escena y en total."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        por_escena = selectors.progreso_resumen(usuario=request.user)
        total = selectors.progreso_total(resumen_por_escena=por_escena)
        return Response(ProgresoResponseSerializer({"escenas": por_escena, "total": total}).data)
