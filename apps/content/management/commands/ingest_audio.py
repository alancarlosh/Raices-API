from django.core.management.base import BaseCommand, CommandError

from apps.content import services
from apps.content.models import ObjetoInteractivo


class Command(BaseCommand):
    help = (
        "Pipeline de ingesta de audio real: toma una grabación fuente (ej. de un "
        "hablante nativo) para un ObjetoInteractivo, genera audio_ogg/audio_m4a "
        "con ffmpeg, y lo deja en 'en_revision' para que un hablante-revisor lo "
        "apruebe y publique desde el admin."
    )

    def add_arguments(self, parser):
        parser.add_argument("objeto_id", type=int, help="ID del ObjetoInteractivo destino")
        parser.add_argument("ruta_audio_fuente", type=str, help="Ruta al archivo de audio fuente")

    def handle(self, *args, **options):
        try:
            objeto = services.objeto_ingerir_audio(
                objeto_id=options["objeto_id"],
                ruta_audio_fuente=options["ruta_audio_fuente"],
            )
        except ObjetoInteractivo.DoesNotExist:
            raise CommandError(f"No existe ObjetoInteractivo con id={options['objeto_id']}")
        except FileNotFoundError as exc:
            raise CommandError(str(exc))

        self.stdout.write(
            self.style.SUCCESS(
                f"Audio generado para '{objeto.palabra}' (id={objeto.id}), "
                f"estado ahora '{objeto.estado}'. Revísalo y publícalo desde el admin."
            )
        )
