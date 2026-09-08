from unittest.mock import patch

import pytest

from apps.content import services
from apps.content.models import ObjetoInteractivo
from apps.content.tests.factories import ObjetoInteractivoFactory

pytestmark = pytest.mark.django_db


def test_objeto_ingerir_audio_actualiza_urls_y_pasa_a_revision(tmp_path, settings):
    settings.MEDIA_BASE_URL = "http://127.0.0.1:8000"
    objeto = ObjetoInteractivoFactory(estado=ObjetoInteractivo.Estado.PUBLICADO)
    fuente = tmp_path / "grabacion.wav"
    fuente.write_bytes(b"contenido-de-audio-de-prueba")

    with patch.object(services, "_transcodificar") as mock_transcodificar:
        resultado = services.objeto_ingerir_audio(objeto_id=objeto.id, ruta_audio_fuente=str(fuente))

    mock_transcodificar.assert_called_once()
    nombre_base = f"{objeto.id}_{objeto.palabra}"
    assert resultado.audio_ogg == f"http://127.0.0.1:8000/media/audio/ingerido/{nombre_base}.ogg"
    assert resultado.audio_m4a == f"http://127.0.0.1:8000/media/audio/ingerido/{nombre_base}.m4a"
    assert resultado.estado == ObjetoInteractivo.Estado.EN_REVISION

    # Persistido de verdad, no solo en el objeto en memoria.
    objeto.refresh_from_db()
    assert objeto.estado == ObjetoInteractivo.Estado.EN_REVISION


def test_objeto_ingerir_audio_falla_si_no_existe_el_archivo_fuente():
    objeto = ObjetoInteractivoFactory()

    with pytest.raises(FileNotFoundError):
        services.objeto_ingerir_audio(objeto_id=objeto.id, ruta_audio_fuente="/no/existe/en/ningun/lado.wav")


def test_objeto_ingerir_audio_falla_si_no_existe_el_objeto():
    with pytest.raises(ObjetoInteractivo.DoesNotExist):
        services.objeto_ingerir_audio(objeto_id=999999, ruta_audio_fuente="/tmp/lo-que-sea.wav")
