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
