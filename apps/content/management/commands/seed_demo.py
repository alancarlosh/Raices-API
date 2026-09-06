from django.core.management.base import BaseCommand

from apps.accounts.models import Usuario
from apps.content.models import Escena, ObjetoInteractivo
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

# ADVERTENCIA: "palabra" abajo son nombres en ESPAÑOL usados como placeholder de
# desarrollo para poder probar la conexión end-to-end con el frontend. NO son
# traducciones reales al totonaco. Deben reemplazarse por el vocabulario y audio
# real una vez que el asesor entregue las grabaciones validadas por hablantes
# nativos — ver progress/services.py y el README para el flujo de moderación.
ESCENAS_SEED = {
    "Cocina": [
        ("silla", "chair_wood_a"),
        ("mesa", "table_wood_a"),
        ("puerta", "door_wood_a"),
        ("ventana", "window_a"),
        ("estufa", "stove_a"),
        ("refrigerador", "fridge_a"),
        ("plato", "plate_a"),
        ("vaso", "cup_a"),
    ],
    "Sala": [
        ("sofa", "sofa_a"),
        ("mesa_centro", "table_coffee_a"),
        ("lampara", "lamp_a"),
        ("televisor", "tv_a"),
        ("cortina", "curtain_a"),
        ("cojin", "cushion_a"),
        ("librero", "bookshelf_a"),
        ("reloj", "clock_wall_a"),
    ],
}


class Command(BaseCommand):
    help = (
        "Crea datos de demo (lengua, escenas, objetos, usuario de prueba) para que "
        "Raices-Front pueda conectarse a la API real en vez de usar fixtures locales. "
        "Idempotente: correrlo varias veces no duplica datos."
    )

    def handle(self, *args, **options):
        lengua, _ = Lengua.objects.get_or_create(
            codigo="toto",
            defaults={
                "nombre": "Totonaco",
                "descripcion": "Lengua placeholder para desarrollo hasta que el asesor "
                "confirme la primera lengua con grabaciones reales.",
            },
        )

        for orden, (nombre_escena, objetos) in enumerate(ESCENAS_SEED.items()):
            escena, _ = Escena.objects.get_or_create(
                nombre=nombre_escena,
                lengua=lengua,
                defaults={
                    "fondo": f"https://cdn.example.com/placeholder/fondos/{nombre_escena.lower()}.png",
                    "orden": orden,
                },
            )

            for i, (palabra, sprite_key) in enumerate(objetos):
                fila, columna = divmod(i, _GRID_COLS)
                ObjetoInteractivo.objects.get_or_create(
                    escena=escena,
                    palabra=palabra,
                    defaults={
                        "lengua": lengua,
                        "sprite_key": sprite_key,
                        "audio_ogg": f"https://cdn.example.com/placeholder/audio/{palabra}.ogg",
                        "audio_m4a": f"https://cdn.example.com/placeholder/audio/{palabra}.m4a",
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
