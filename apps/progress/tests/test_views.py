import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UsuarioFactory
from apps.content.tests.factories import EscenaFactory, ObjetoInteractivoFactory

pytestmark = pytest.mark.django_db


def test_progreso_devuelve_escenas_y_total():
    escena = EscenaFactory()
    objeto = ObjetoInteractivoFactory(escena=escena, palabra="silla")
    usuario = UsuarioFactory()
    client = APIClient()
    client.force_authenticate(user=usuario)

    client.post(f"/api/objetos/{objeto.id}/descubrir/")
    client.post(f"/api/objetos/{objeto.id}/intento-escritura/", {"texto_ingresado": "silla"}, format="json")

    respuesta = client.get("/api/progreso/")

    assert respuesta.status_code == 200
    assert "escenas" in respuesta.data
    assert "total" in respuesta.data
    fila = next(e for e in respuesta.data["escenas"] if e["escena_id"] == escena.id)
    assert fila["objetos_descubiertos"] == 1
    assert fila["objetos_dominados"] == 1
    assert respuesta.data["total"]["objetos_dominados"] == 1
