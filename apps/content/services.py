import subprocess
from pathlib import Path

from django.conf import settings

from .models import ObjetoInteractivo

AUDIO_INGERIDO_DIR = "audio/ingerido"


def _transcodificar(fuente: Path, destino_ogg: Path, destino_m4a: Path) -> None:
    """Genera OGG/Opus (formato principal) y AAC/M4A (fallback Safari/iOS) a
    partir de un archivo de audio fuente, en una pasada de ffmpeg por cada uno."""
    destino_ogg.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(fuente), "-c:a", "libopus", "-b:a", "48k", str(destino_ogg)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(fuente), "-c:a", "aac", "-b:a", "96k", str(destino_m4a)],
        check=True,
        capture_output=True,
    )


def objeto_ingerir_audio(*, objeto_id: int, ruta_audio_fuente: str) -> ObjetoInteractivo:
    """Pipeline real de ingesta de audio: toma una grabación fuente (p. ej. de un
    hablante nativo), genera audio_ogg/audio_m4a con ffmpeg, y deja el objeto en
    'en_revision' para que un hablante-revisor lo apruebe desde el admin —
    nunca se publica automáticamente.
    """
    objeto = ObjetoInteractivo.objects.get(pk=objeto_id)

    fuente = Path(ruta_audio_fuente)
    if not fuente.is_file():
        raise FileNotFoundError(f"No se encontró el archivo fuente: {fuente}")

    nombre_base = f"{objeto.id}_{objeto.palabra}"
    destino_ogg = Path(settings.MEDIA_ROOT) / AUDIO_INGERIDO_DIR / f"{nombre_base}.ogg"
    destino_m4a = Path(settings.MEDIA_ROOT) / AUDIO_INGERIDO_DIR / f"{nombre_base}.m4a"

    _transcodificar(fuente, destino_ogg, destino_m4a)

    base_url = f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL}"
    objeto.audio_ogg = f"{base_url}{AUDIO_INGERIDO_DIR}/{nombre_base}.ogg"
    objeto.audio_m4a = f"{base_url}{AUDIO_INGERIDO_DIR}/{nombre_base}.m4a"
    objeto.estado = ObjetoInteractivo.Estado.EN_REVISION
    objeto.save()
    return objeto
