import unicodedata

from apps.content.selectors import objeto_get

from .models import IntentoEscritura, ProgresoUsuario


def progreso_marcar_descubierto(*, usuario, objeto_id: int) -> ProgresoUsuario:
    objeto = objeto_get(objeto_id=objeto_id)
    progreso, _ = ProgresoUsuario.objects.get_or_create(usuario=usuario, objeto=objeto)
    return progreso


def intento_escritura_registrar(*, usuario, objeto_id: int, texto_ingresado: str) -> IntentoEscritura:
    """Compara la escritura del usuario contra la palabra de referencia.

    Ambos strings se normalizan a NFC antes de comparar. Nunca se usa
    unidecode ni se eliminan diacríticos: el saltillo y las vocales largas
    cambian el significado de la palabra en varias lenguas originarias.
    """
    objeto = objeto_get(objeto_id=objeto_id)

    texto_normalizado = unicodedata.normalize("NFC", texto_ingresado)
    palabra_normalizada = unicodedata.normalize("NFC", objeto.palabra)
    correcto = texto_normalizado == palabra_normalizada

    return IntentoEscritura.objects.create(
        usuario=usuario,
        objeto=objeto,
        texto_ingresado=texto_normalizado,
        correcto=correcto,
    )
