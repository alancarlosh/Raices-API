from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

pytestmark = pytest.mark.django_db


def test_media_se_sirve_localmente_en_desarrollo():
    destino_dir = Path(settings.MEDIA_ROOT) / "audio" / "placeholder"
    destino_dir.mkdir(parents=True, exist_ok=True)
    archivo = destino_dir / "_test_media_route.ogg"
    archivo.write_bytes(b"contenido-de-prueba")

    try:
        respuesta = Client().get("/media/audio/placeholder/_test_media_route.ogg")
        assert respuesta.status_code == 200
    finally:
        archivo.unlink()


def test_media_devuelve_404_si_no_existe():
    respuesta = Client().get("/media/audio/placeholder/no-existe-este-archivo.ogg")
    assert respuesta.status_code == 404
