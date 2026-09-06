from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from .models import Escena, ObjetoInteractivo


def escena_get_publicada(*, escena_id: int) -> Escena:
    """Devuelve una escena con sus objetos publicados precargados (evita N+1)."""
    objetos_publicados = ObjetoInteractivo.objects.filter(
        estado=ObjetoInteractivo.Estado.PUBLICADO,
    ).select_related("lengua")
    return get_object_or_404(
        Escena.objects.select_related("lengua").prefetch_related(
            Prefetch("objetos", queryset=objetos_publicados),
        ),
        pk=escena_id,
    )


def objeto_get(*, objeto_id: int) -> ObjetoInteractivo:
    return get_object_or_404(ObjetoInteractivo.objects.select_related("escena", "lengua"), pk=objeto_id)
