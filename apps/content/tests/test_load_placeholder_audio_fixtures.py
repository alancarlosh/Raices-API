from pathlib import Path

from django.core.management import call_command


def test_carga_los_fixtures_committeados_a_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    call_command("load_placeholder_audio_fixtures")

    destino = Path(settings.MEDIA_ROOT) / "audio" / "placeholder"
    archivos = list(destino.glob("*"))
    assert len(archivos) == 30
    assert (destino / "silla.ogg").exists()
    assert (destino / "silla.m4a").exists()
