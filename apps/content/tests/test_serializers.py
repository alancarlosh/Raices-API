"""Pruebas del serializador de objetos interactivos.

Lo que se prueba aquí es el campo `teclado`, que es el que decide con qué
alfabeto se escribe cada palabra. No es cosmético: es lo que separa un
ejercicio que se puede completar de uno que no.
"""
import pytest

from apps.content.serializers import ObjetoInteractivoSerializer
from apps.content.tests.factories import ObjetoInteractivoFactory

pytestmark = pytest.mark.django_db

def test_teclado_es_espanol_mientras_la_palabra_sea_placeholder():
    """Lo que desbloquea el ejercicio de escritura.

    Medido el 2026-11-09: con `palabra` conteniendo el placeholder en
    español y un teclado totonaco (sin b c d f g v z ni tildes), 56 de
    las 87 palabras del catálogo eran IMPOSIBLES de escribir.
    """
    obj = ObjetoInteractivoFactory(palabra="comal", glosa_es="comal")
    assert ObjetoInteractivoSerializer(obj).data["teclado"] == "espanol"


def test_teclado_pasa_a_totonaco_en_cuanto_la_palabra_es_real():
    """Sin desplegar nada: basta con que la fila reciba su palabra."""
    obj = ObjetoInteractivoFactory(palabra="palhcla", glosa_es="comal")
    assert ObjetoInteractivoSerializer(obj).data["teclado"] == "totonaco"


def test_una_fila_sin_glosa_no_se_marca_como_placeholder():
    """Si glosa_es está vacía no hay nada contra lo que comparar; tratar
    eso como placeholder pondría teclado español a una palabra real."""
    obj = ObjetoInteractivoFactory(palabra="palhcla", glosa_es="")
    assert ObjetoInteractivoSerializer(obj).data["teclado"] == "totonaco"
