from django.db.models import Count, Q

from apps.content.models import Escena, ObjetoInteractivo

from .models import ProgresoUsuario


def progreso_resumen(*, usuario) -> list[dict]:
    """% de objetos descubiertos por escena para el usuario dado."""
    total_publicado = Q(objetos__estado=ObjetoInteractivo.Estado.PUBLICADO)
    descubierto_por_usuario = Q(
        objetos__progresos__usuario=usuario,
        objetos__estado=ObjetoInteractivo.Estado.PUBLICADO,
    )

    escenas = Escena.objects.annotate(
        total_objetos=Count("objetos", filter=total_publicado, distinct=True),
        objetos_descubiertos=Count("objetos", filter=descubierto_por_usuario, distinct=True),
    ).select_related("lengua")

    resumen = []
    for escena in escenas:
        porcentaje = (
            round(100 * escena.objetos_descubiertos / escena.total_objetos, 1)
            if escena.total_objetos
            else 0.0
        )
        resumen.append(
            {
                "escena_id": escena.id,
                "escena_nombre": escena.nombre,
                "lengua": escena.lengua.codigo,
                "total_objetos": escena.total_objetos,
                "objetos_descubiertos": escena.objetos_descubiertos,
                "porcentaje": porcentaje,
            }
        )
    return resumen


def usuario_ha_descubierto(*, usuario, objeto_id: int) -> bool:
    return ProgresoUsuario.objects.filter(usuario=usuario, objeto_id=objeto_id).exists()
