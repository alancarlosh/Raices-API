from django.db.models import Avg, Count, Min
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import MedicionRendimiento
from .serializers import MedicionRendimientoSerializer


class MedicionRendimientoCrearView(generics.CreateAPIView):
    """Recibe el resumen de rendimiento de una sesión. POST /api/rendimiento/

    El cliente manda UNA medida por escena y por carga de página, cuando ya
    lleva suficientes segundos andando. El tope de peticiones de abajo no
    está puesto contra un atacante — hace falta sesión iniciada — sino
    contra un cliente con un bucle mal escrito: sin él, un fallo mío en el
    front podría llenar la base de un plan gratuito en una tarde de clase.
    """

    serializer_class = MedicionRendimientoSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "rendimiento"

    def perform_create(self, serializer):
        # El usuario NO viaja en el cuerpo: se toma del token. Si viajara,
        # cualquiera con sesión podría escribir mediciones a nombre de otro
        # y la tabla por alumno dejaría de significar nada.
        serializer.save(usuario=self.request.user)


class ResumenRendimientoView(APIView):
    """Tabla agregada para decidir QUÉ optimizar. GET /api/rendimiento/resumen/

    Solo personal: son datos de los equipos de terceros, y además la
    pregunta que responde ("qué máquinas sufren") es de quien desarrolla,
    no del alumno.

    Agrupa por escena y por GPU, que es el corte que de verdad separa
    equipos; agrupar por usuario respondería "quién tiene mala suerte", no
    "qué hay que arreglar".

    Se ordena por `p5_medio` ASCENDENTE a propósito: arriba sale lo peor.
    Una tabla de rendimiento ordenada por lo bueno se lee y no se actúa.
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        filas = (
            MedicionRendimiento.objects
            .values("escena", "gpu")
            .annotate(
                equipos=Count("usuario", distinct=True),
                medidas=Count("id"),
                p50_medio=Avg("fps_p50"),
                p5_medio=Avg("fps_p5"),
                peor=Min("fps_min"),
                dpr_medio=Avg("dpr"),
            )
            .order_by("p5_medio")
        )
        return Response({
            "total": MedicionRendimiento.objects.count(),
            "filas": [
                {
                    **f,
                    "p50_medio": round(f["p50_medio"], 1),
                    "p5_medio": round(f["p5_medio"], 1),
                    "dpr_medio": round(f["dpr_medio"], 2),
                }
                for f in filas
            ],
        })
