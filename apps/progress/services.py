import unicodedata

from apps.content.selectors import objeto_get

from .models import IntentoEscritura, ProgresoUsuario


def progreso_marcar_descubierto(*, usuario, objeto_id: int) -> ProgresoUsuario:
    objeto = objeto_get(objeto_id=objeto_id)
    progreso, _ = ProgresoUsuario.objects.get_or_create(usuario=usuario, objeto=objeto)
    return progreso


# LAS TRES FORMAS DEL SALTILLO, unificadas antes de comparar.
#
# El saltillo (la glotal) es UNA LETRA del tutunakú, y en la práctica se
# escribe con tres puntos de código distintos:
#   U+A78C  ꞌ  saltillo minúscula — lo que emite el teclado del proyecto
#   U+2019  ’  comilla tipográfica derecha
#   U+0027  '  apóstrofo ASCII
#
# MEDIDO sobre la norma del INALI 2017 (170 pp., pdftotext): U+A78C no
# aparece NI UNA VEZ; hay 1744 de U+2019 y 238 de U+0027. Pero esos 1744
# son las comillas que el maquetador pone al componer el libro, no una
# decisión ortográfica: el mismo PDF los usa para las glosas ('viento',
# 'este'). La norma llama a la letra "' (glotal)" y nunca fija un punto
# de código.
#
# O sea que NADIE puede garantizar cuál es "el" carácter. Lo que sí se
# puede garantizar es que el alumno no falle por esto: escribe el
# saltillo del teclado, la semilla puede traerlo de un diccionario con
# apóstrofo ASCII, y hoy eso daría "incorrecto" sin que ni él ni el
# asesor pudieran ver la diferencia en pantalla — los tres se dibujan
# casi igual.
#
# Esto NO elimina diacríticos ni hace la comparación laxa: sigue sin
# usarse unidecode, y el saltillo sigue siendo obligatorio. Lo único que
# se unifica es con qué byte se escribe la misma letra.
_SALTILLOS = {
    "\u2019": "\uA78C",   # ’ comilla tipográfica derecha
    "\u0027": "\uA78C",   # ' apóstrofo ASCII
    "\u02BC": "\uA78C",   # ʼ letra apóstrofo modificadora
    "\uA78B": "\uA78C",   # Ꞌ saltillo MAYÚSCULA -> minúscula
}


def normalizar_escritura(texto: str) -> str:
    """NFC + una sola forma del saltillo. Ver `_SALTILLOS`."""
    texto = unicodedata.normalize("NFC", texto)
    for origen, destino in _SALTILLOS.items():
        texto = texto.replace(origen, destino)
    return texto


def intento_escritura_registrar(*, usuario, objeto_id: int, texto_ingresado: str) -> IntentoEscritura:
    """Compara la escritura del usuario contra la palabra de referencia.

    Ambos strings se normalizan a NFC antes de comparar. Nunca se usa
    unidecode ni se eliminan diacríticos: el saltillo y las vocales largas
    cambian el significado de la palabra en varias lenguas originarias.

    Lo único que se unifica además del NFC son las tres grafías del
    saltillo, que son la MISMA letra escrita con bytes distintos. Ver
    `normalizar_escritura`.
    """
    objeto = objeto_get(objeto_id=objeto_id)

    texto_normalizado = normalizar_escritura(texto_ingresado)
    palabra_normalizada = normalizar_escritura(objeto.palabra)
    correcto = texto_normalizado == palabra_normalizada

    return IntentoEscritura.objects.create(
        usuario=usuario,
        objeto=objeto,
        texto_ingresado=texto_normalizado,
        correcto=correcto,
    )
