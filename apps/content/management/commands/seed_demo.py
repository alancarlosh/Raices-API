from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import Usuario
from apps.content.models import Escena, ObjetoInteractivo
from apps.content.seed_data import ESCENAS_SEED
from apps.languages.models import Lengua

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo12345!"

# Layout en grilla sobre un lienzo de referencia de 960x540 (el frontend puede
# reescalar como necesite; lo importante para el sprint es tener x/y/width/height
# consistentes para probar la conexión real).
_GRID_COLS = 4
_CELL_W, _CELL_H = 200, 160
_OBJ_W, _OBJ_H = 64, 64
_ORIGIN_X, _ORIGIN_Y = 60, 60


def _url_audio_placeholder(palabra: str, extension: str) -> str:
    """Apunta al audio TTS generado por `generate_placeholder_audio`, servido
    localmente por Django (ver MEDIA_BASE_URL/MEDIA_URL en settings) — no un
    dominio inventado que nunca resuelve."""
    return f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL}audio/placeholder/{palabra}.{extension}"


class Command(BaseCommand):
    help = (
        "Crea datos de demo (lengua, escenas, objetos, usuario de prueba) para que "
        "Raices-Front pueda conectarse a la API real en vez de usar fixtures locales. "
        "Idempotente: correrlo varias veces no duplica datos. Corre antes "
        "'python manage.py generate_placeholder_audio' para que las URLs de "
        "audio_ogg/audio_m4a que este comando genera resuelvan a archivos reales."
    )

    def handle(self, *args, **options):
        lengua, _ = Lengua.objects.update_or_create(
            codigo="toto",
            defaults={
                "nombre": "Totonaco",
                "descripcion": "Primera lengua objetivo confirmada del proyecto. Las palabras "
                "de este seed son placeholders en español mientras se integra el "
                "vocabulario y audio real validado por el asesor y hablantes nativos.",
            },
        )

        for orden, (nombre_escena, objetos) in enumerate(ESCENAS_SEED.items()):
            codigo_escena = nombre_escena.lower()
            escena, _ = Escena.objects.update_or_create(
                codigo=codigo_escena,
                defaults={
                    "nombre": nombre_escena,
                    "lengua": lengua,
                    "fondo": f"https://cdn.example.com/placeholder/fondos/{codigo_escena}.png",
                    "orden": orden,
                },
            )

            palabras_vigentes = [palabra for palabra, _ in objetos]
            escena.objetos.exclude(palabra__in=palabras_vigentes).delete()

            for i, (palabra, sprite_key) in enumerate(objetos):
                fila, columna = divmod(i, _GRID_COLS)
                # update_or_create (no get_or_create): sprite_key y otros campos
                # placeholder siguen ajustándose mientras se coordina con el
                # frontend, así que rehacer el seed debe corregir filas existentes.
                ObjetoInteractivo.objects.update_or_create(
                    escena=escena,
                    palabra=palabra,
                    defaults={
                        "lengua": lengua,
                        "sprite_key": sprite_key,
                        "audio_ogg": _url_audio_placeholder(palabra, "ogg"),
                        "audio_m4a": _url_audio_placeholder(palabra, "m4a"),
                        "x": _ORIGIN_X + columna * _CELL_W,
                        "y": _ORIGIN_Y + fila * _CELL_H,
                        "width": _OBJ_W,
                        "height": _OBJ_H,
                        "estado": ObjetoInteractivo.Estado.PUBLICADO,
                    },
                )

            self.stdout.write(self.style.SUCCESS(f"Escena '{nombre_escena}' lista con {len(objetos)} objetos."))

        usuario, creado = Usuario.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"email": "demo@example.com", "rol": Usuario.Rol.APRENDIZ},
        )
        usuario.set_password(DEMO_PASSWORD)
        usuario.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario de prueba {'creado' if creado else 'actualizado'}: "
                f"username='{DEMO_USERNAME}' password='{DEMO_PASSWORD}'"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Las palabras sembradas son placeholders en español, NO traducciones "
                "reales al totonaco — reemplazar cuando llegue el contenido validado."
            )
        )
