from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors, services
from .serializers import (
    IntentoEscrituraInputSerializer,
    IntentoEscrituraResultSerializer,
    ProgresoResumenSerializer,
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
    """GET /api/progreso/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        resumen = selectors.progreso_resumen(usuario=request.user)
        return Response(ProgresoResumenSerializer(resumen, many=True).data)
