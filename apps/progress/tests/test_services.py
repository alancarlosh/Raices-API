import unicodedata

import pytest

from apps.accounts.tests.factories import UsuarioFactory
from apps.content.tests.factories import ObjetoInteractivoFactory
from apps.progress import services
from apps.progress.models import IntentoEscritura, ProgresoUsuario

pytestmark = pytest.mark.django_db


def test_intento_escritura_correcto_cuando_coincide_exacto():
    objeto = ObjetoInteractivoFactory(palabra="chiwix")
    usuario = UsuarioFactory()

    intento = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado="chiwix"
    )

    assert intento.correcto is True
    assert IntentoEscritura.objects.count() == 1


def test_intento_escritura_valida_contra_palabra_no_glosa_es():
    # glosa_es es solo la etiqueta en español para la UI; la escritura del
    # usuario nunca debe compararse contra ella, sino contra `palabra`.
    objeto = ObjetoInteractivoFactory(palabra="chiwix", glosa_es="silla")
    usuario = UsuarioFactory()

    intento_glosa = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado="silla"
    )
    intento_palabra = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado="chiwix"
    )

    assert intento_glosa.correcto is False
    assert intento_palabra.correcto is True


def test_intento_escritura_es_sensible_al_saltillo():
    # U+A78C = LATIN SMALL LETTER SALTILLO. No es decorativo: distingue palabras.
    objeto = ObjetoInteractivoFactory(palabra="aꞌa")

    usuario = UsuarioFactory()
    intento = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado="aa"
    )

    assert intento.correcto is False


def test_intento_escritura_normaliza_nfc_antes_de_comparar():
    # Forma NFD (letra + acento combinante) debe considerarse igual a NFC.
    forma_nfc = unicodedata.normalize("NFC", "á")
    forma_nfd = unicodedata.normalize("NFD", "á")
    assert forma_nfc != forma_nfd  # confirma que son secuencias de bytes distintas

    objeto = ObjetoInteractivoFactory(palabra=forma_nfc)
    usuario = UsuarioFactory()

    intento = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado=forma_nfd
    )

    assert intento.correcto is True


def test_progreso_marcar_descubierto_es_idempotente():
    objeto = ObjetoInteractivoFactory()
    usuario = UsuarioFactory()

    services.progreso_marcar_descubierto(usuario=usuario, objeto_id=objeto.id)
    services.progreso_marcar_descubierto(usuario=usuario, objeto_id=objeto.id)

    assert ProgresoUsuario.objects.filter(usuario=usuario, objeto=objeto).count() == 1


@pytest.mark.parametrize(
    "grafia_fuente, nombre",
    [
        ("a'a", "apóstrofo ASCII U+0027"),
        ("a’a", "comilla tipográfica U+2019"),
        ("aʼa", "letra apóstrofo modificadora U+02BC"),
        ("aꞌa", "saltillo U+A78C, el que emite el teclado"),
    ],
)
def test_las_tres_grafias_del_saltillo_son_la_misma_letra(grafia_fuente, nombre):
    """El alumno no puede fallar por con qué BYTE se escribió la glotal.

    Las fuentes del proyecto no coinciden entre sí: el teclado emite
    U+A78C, los diccionarios de Aschmann usan apóstrofo ASCII y el PDF de
    la norma del INALI sale maquetado con U+2019. Los tres se dibujan casi
    igual en pantalla, así que un fallo por esto sería invisible tanto
    para el alumno como para quien revise.

    Esto NO relaja la comparación: el saltillo sigue siendo obligatorio
    (lo prueba test_intento_escritura_es_sensible_al_saltillo) y no se
    quitan diacríticos. Solo se unifica la forma de la misma letra.
    """
    objeto = ObjetoInteractivoFactory(palabra=grafia_fuente)
    usuario = UsuarioFactory()

    # El usuario escribe SIEMPRE con la tecla del proyecto (U+A78C).
    intento = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado="aꞌa"
    )

    assert intento.correcto is True, f"falló contra {nombre}"


def test_el_saltillo_sigue_sin_poder_omitirse():
    """Guardia de la guardia: unificar grafías no debe volver laxa la
    comparación. Si esto se rompiera, "aa" pasaría como "aꞌa" y el
    ejercicio dejaría de enseñar la glotal, que es justo lo difícil."""
    objeto = ObjetoInteractivoFactory(palabra="a'a")
    usuario = UsuarioFactory()
    intento = services.intento_escritura_registrar(
        usuario=usuario, objeto_id=objeto.id, texto_ingresado="aa"
    )
    assert intento.correcto is False
