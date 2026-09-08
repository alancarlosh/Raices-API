import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.content.seed_data import palabras_unicas

PLACEHOLDER_DIR = "audio/placeholder"
VOZ = "Paulina"  # voz es-MX incluida en macOS


class Command(BaseCommand):
    help = (
        "Genera clips de audio placeholder (TTS vía 'say', NO grabaciones reales) "
        "para las palabras del seed de desarrollo, con 'say' + ffmpeg. Solo para "
        "desarrollo local en macOS; en producción el audio real lo sirve un CDN. "
        "Correr antes de 'seed_demo' para que sus URLs de audio resuelvan."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Regenerar aunque ya existan los archivos"
        )

    def handle(self, *args, **options):
        for binario in ("say", "ffmpeg"):
            if shutil.which(binario) is None:
                raise CommandError(
                    f"'{binario}' no está instalado o no está en PATH. Este comando es "
                    "solo para desarrollo local en macOS."
                )

        salida_dir = Path(settings.MEDIA_ROOT) / PLACEHOLDER_DIR
        salida_dir.mkdir(parents=True, exist_ok=True)

        generados = 0
        for palabra in palabras_unicas():
            destino_ogg = salida_dir / f"{palabra}.ogg"
            destino_m4a = salida_dir / f"{palabra}.m4a"
            if destino_ogg.exists() and destino_m4a.exists() and not options["force"]:
                continue

            with tempfile.NamedTemporaryFile(suffix=".aiff") as fuente_tts:
                subprocess.run(["say", "-v", VOZ, "-o", fuente_tts.name, palabra], check=True)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", fuente_tts.name, "-c:a", "libopus", "-b:a", "48k", str(destino_ogg)],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["ffmpeg", "-y", "-i", fuente_tts.name, "-c:a", "aac", "-b:a", "96k", str(destino_m4a)],
                    check=True,
                    capture_output=True,
                )

            generados += 1
            self.stdout.write(self.style.SUCCESS(f"Generado: {palabra}"))

        self.stdout.write(
            self.style.SUCCESS(f"{generados} palabra(s) generada(s) en {salida_dir} (el resto ya existía).")
        )
        self.stdout.write(
            self.style.WARNING(
                "Audio generado con TTS ('say') como placeholder de desarrollo — NO son "
                "grabaciones reales de hablantes nativos. Reemplazar vía 'ingest_audio' "
                "cuando lleguen las grabaciones validadas del asesor."
            )
        )
