import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UsuarioFactory
from apps.content.models import ObjetoInteractivo
from apps.content.tests.factories import EscenaFactory, ObjetoInteractivoFactory

pytestmark = pytest.mark.django_db


def _client_autenticado(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


def test_escena_detail_devuelve_solo_objetos_publicados():
    escena = EscenaFactory()
    ObjetoInteractivoFactory(escena=escena, palabra="publicado", estado=ObjetoInteractivo.Estado.PUBLICADO)
    ObjetoInteractivoFactory(escena=escena, palabra="borrador", estado=ObjetoInteractivo.Estado.BORRADOR)
    usuario = UsuarioFactory()

    respuesta = _client_autenticado(usuario).get(f"/api/escenas/{escena.id}/")

    assert respuesta.status_code == 200
    palabras = [o["palabra"] for o in respuesta.data["objetos"]]
    assert palabras == ["publicado"]


def test_escena_detail_expone_palabra_y_glosa_es_por_separado():
    # EscenaDetailView usa cache_page keyed solo por URL: como sqlite reutiliza
    # rowids entre tests (cada uno corre en su propia transacción con rollback),
    # dos escenas de tests distintos pueden compartir id y servir una respuesta
    # cacheada de otro test. Se limpia para que este test no dependa del orden.
    cache.clear()
    escena = EscenaFactory()
    ObjetoInteractivoFactory(
        escena=escena,
        palabra="tasknu",
        glosa_es="silla",
        estado=ObjetoInteractivo.Estado.PUBLICADO,
    )
    usuario = UsuarioFactory()

    respuesta = _client_autenticado(usuario).get(f"/api/escenas/{escena.id}/")

    objeto = respuesta.data["objetos"][0]
    assert objeto["palabra"] == "tasknu"
    assert objeto["glosa_es"] == "silla"


def test_escena_detail_no_incurre_en_n_mas_1(django_assert_max_num_queries):
    escena = EscenaFactory()
    for i in range(10):
        ObjetoInteractivoFactory(escena=escena, palabra=f"objeto{i}")
    usuario = UsuarioFactory()

    # 1 query por la escena + 1 por el prefetch de objetos, sin importar cuántos objetos haya.
    with django_assert_max_num_queries(3):
        _client_autenticado(usuario).get(f"/api/escenas/{escena.id}/")


def test_escena_detail_requiere_autenticacion():
    escena = EscenaFactory()

    respuesta = APIClient().get(f"/api/escenas/{escena.id}/")

    assert respuesta.status_code == 401


def test_escena_list_expone_codigo_para_navegacion():
    EscenaFactory(codigo="cocina", nombre="Cocina", orden=0)
    EscenaFactory(codigo="sala", nombre="Sala", orden=1)
    usuario = UsuarioFactory()

    respuesta = _client_autenticado(usuario).get("/api/escenas/")

    codigos = [e["codigo"] for e in respuesta.data]
    assert codigos == ["cocina", "sala"]
    assert "id" in respuesta.data[0]
