import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "audio_placeholder"
PLACEHOLDER_DIR = "audio/placeholder"


class Command(BaseCommand):
    help = (
        "Copia el audio placeholder ya generado (committeado en "
        "apps/content/fixtures/audio_placeholder/) a MEDIA_ROOT. Portable — no "
        "depende de 'say' (macOS) ni de ffmpeg, así que es lo que corre el build "
        "de Render (filesystem efímero) en vez de 'generate_placeholder_audio'. "
        "Para regenerar el audio fuente en sí (ej. si cambian las palabras del "
        "seed), sigue usando 'generate_placeholder_audio' en macOS y vuelve a "
        "committear los archivos resultantes en el directorio de fixtures."
    )

    def handle(self, *args, **options):
        destino_dir = Path(settings.MEDIA_ROOT) / PLACEHOLDER_DIR
        destino_dir.mkdir(parents=True, exist_ok=True)

        archivos = sorted(FIXTURES_DIR.glob("*"))
        for archivo in archivos:
            shutil.copyfile(archivo, destino_dir / archivo.name)

        self.stdout.write(self.style.SUCCESS(f"{len(archivos)} archivo(s) copiado(s) a {destino_dir}."))
