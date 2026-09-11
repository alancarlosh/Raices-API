from django.db.models import Count, Q

from apps.content.models import Escena, ObjetoInteractivo

from .models import IntentoEscritura, ProgresoUsuario


def _objetos_dominados_ids(*, usuario) -> set[int]:
    """Un objeto está 'dominado' si el intento de escritura MÁS RECIENTE del
    usuario para ese objeto fue correcto. Deliberadamente no es "al menos un
    acierto alguna vez": eso dejaría marcada como dominada una palabra que el
    usuario acertó una vez y luego falló repetidamente, lo cual contradice el
    diseño ya documentado en IntentoEscritura ("el dominio se DERIVA del
    historial, no es un booleano fijo").
    """
    vistos = set()
    dominados = set()
    intentos = (
        IntentoEscritura.objects.filter(usuario=usuario)
        .order_by("objeto_id", "-creado_en")
        .only("objeto_id", "correcto")
    )
    for intento in intentos:
        if intento.objeto_id in vistos:
            continue
        vistos.add(intento.objeto_id)
        if intento.correcto:
            dominados.add(intento.objeto_id)
    return dominados


def progreso_resumen(*, usuario) -> list[dict]:
    """% de objetos descubiertos y dominados por escena para el usuario dado."""
    total_publicado = Q(objetos__estado=ObjetoInteractivo.Estado.PUBLICADO)
    descubierto_por_usuario = Q(
        objetos__progresos__usuario=usuario,
        objetos__estado=ObjetoInteractivo.Estado.PUBLICADO,
    )

    escenas = (
        Escena.objects.annotate(
            total_objetos=Count("objetos", filter=total_publicado, distinct=True),
            objetos_descubiertos=Count("objetos", filter=descubierto_por_usuario, distinct=True),
        )
        .select_related("lengua")
        .prefetch_related("objetos")
    )

    dominados_ids = _objetos_dominados_ids(usuario=usuario)

    resumen = []
    for escena in escenas:
        objetos_dominados = sum(
            1
            for objeto in escena.objetos.all()
            if objeto.estado == ObjetoInteractivo.Estado.PUBLICADO and objeto.id in dominados_ids
        )
        resumen.append(
            {
                "escena_id": escena.id,
                "escena_nombre": escena.nombre,
                "lengua": escena.lengua.codigo,
                "total_objetos": escena.total_objetos,
                "objetos_descubiertos": escena.objetos_descubiertos,
                "porcentaje": _porcentaje(escena.objetos_descubiertos, escena.total_objetos),
                "objetos_dominados": objetos_dominados,
                "porcentaje_dominado": _porcentaje(objetos_dominados, escena.total_objetos),
            }
        )
    return resumen


def _porcentaje(parte: int, total: int) -> float:
    return round(100 * parte / total, 1) if total else 0.0


def progreso_total(*, resumen_por_escena: list[dict]) -> dict:
    """Agrega el resumen por escena en un total global — suma simple, sin
    volver a consultar la base de datos."""
    total_objetos = sum(e["total_objetos"] for e in resumen_por_escena)
    objetos_descubiertos = sum(e["objetos_descubiertos"] for e in resumen_por_escena)
    objetos_dominados = sum(e["objetos_dominados"] for e in resumen_por_escena)
    return {
        "total_objetos": total_objetos,
        "objetos_descubiertos": objetos_descubiertos,
        "porcentaje": _porcentaje(objetos_descubiertos, total_objetos),
        "objetos_dominados": objetos_dominados,
        "porcentaje_dominado": _porcentaje(objetos_dominados, total_objetos),
    }


def usuario_ha_descubierto(*, usuario, objeto_id: int) -> bool:
    return ProgresoUsuario.objects.filter(usuario=usuario, objeto_id=objeto_id).exists()
