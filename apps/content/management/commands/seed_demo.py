from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import Usuario
from apps.content.models import Escena, ObjetoInteractivo
from apps.content.seed_data import ESCENAS_SEED
from apps.languages.models import Lengua
from apps.progress.models import IntentoEscritura, ProgresoUsuario

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo12345!"

# Layout en grilla sobre un lienzo de referencia de 960x540 (el frontend puede
# reescalar como necesite; lo importante para el sprint es tener x/y/width/height
# consistentes para probar la conexión real).
_GRID_COLS = 4
_CELL_W, _CELL_H = 200, 160
_OBJ_W, _OBJ_H = 64, 64
_ORIGIN_X, _ORIGIN_Y = 60, 60


# Muestra de progreso para la cuenta `demo`, por si hay que enseñar la
# pantalla de progreso tras una recuperación en frío de la base. No se siembra
# salvo que se pida con --con-progreso: ver la nota en add_arguments.
#
# La forma está elegida para que SE RECONOZCA como dato de demostración si
# alguien mira la base: pocos objetos, repartidos en tres escenas de ocho,
# ninguna escena al 100%, y descubiertos > dominados siempre. No se parece a
# una sesión de uso real porque no pretende parecerlo.
#
# (escena, cuántos descubrir, cuántos de esos dominar)
_MUESTRA_PROGRESO = [
    ("cocina", 4, 2),
    ("sala", 3, 1),
    ("huerto", 2, 1),
]
# Un objeto descubierto con un intento FALLIDO como último, para que la
# pantalla muestre por qué "descubierto" y "dominado" son métricas distintas
# y no solo dos números que casi coinciden.
_ESCENA_INTENTO_FALLIDO = "cocina"


def _progreso_asociado(objetos) -> tuple[int, int]:
    """Cuántas filas de progreso/escritura se llevaría por cascada borrar
    estos objetos — para poder decirlo en voz alta antes de hacerlo, en vez
    de que el daño sea invisible."""
    ids = list(objetos.values_list("id", flat=True))
    if not ids:
        return 0, 0
    return (
        ProgresoUsuario.objects.filter(objeto_id__in=ids).count(),
        IntentoEscritura.objects.filter(objeto_id__in=ids).count(),
    )


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

    def add_arguments(self, parser):
        parser.add_argument(
            "--con-progreso",
            action="store_true",
            help=(
                "Siembra una muestra de progreso para la cuenta 'demo' (unos objetos "
                "descubiertos y dominados en tres escenas). Para qué: ProgresoUsuario e "
                "IntentoEscritura NO están en ninguna semilla, así que si la base se "
                "recrea --y la de Render es de plan gratuito, ya caducó una vez-- la "
                "pantalla de progreso aparece en ceros y la demo en vivo deja de "
                "parecerse a la Figura 4.3 de la tesis. OPT-IN a propósito, y fuera del "
                "buildCommand de render.yaml: sembrar progreso por defecto sería "
                "falsear datos de uso en cualquier otro contexto."
            ),
        )
        parser.add_argument(
            "--purgar",
            action="store_true",
            help=(
                "BORRA de verdad los objetos que ya no están en ESCENAS_SEED, en vez de "
                "marcarlos como 'retirado'. DESTRUCTIVO: ProgresoUsuario e IntentoEscritura "
                "apuntan a ObjetoInteractivo con CASCADE, así que se lleva también el "
                "progreso y los intentos de escritura de los usuarios que practicaron esas "
                "palabras. Sólo para limpiar una base local; nunca en el deploy."
            ),
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

        for orden, (codigo_escena, datos) in enumerate(ESCENAS_SEED.items()):
            nombre_escena = datos["nombre"]
            objetos = datos["objetos"]
            escena, _ = Escena.objects.update_or_create(
                codigo=codigo_escena,
                defaults={
                    "nombre": nombre_escena,
                    "lengua": lengua,
                    "fondo": f"https://cdn.example.com/placeholder/fondos/{codigo_escena}.png",
                    "orden": orden,
                },
            )

            palabras_vigentes = [palabra for palabra, _, _ in objetos]
            sobrantes = escena.objetos.exclude(palabra__in=palabras_vigentes)

            # NO se borra por defecto. ProgresoUsuario e IntentoEscritura
            # apuntan a ObjetoInteractivo con on_delete=CASCADE, y este
            # comando corre en CADA build de Render (ver render.yaml): un
            # `.delete()` aquí significa que cualquier cambio de vocabulario
            # —no sólo la poda del Baño de octubre, y vamos a seguir
            # moviendo vocabulario— se lleva por delante el progreso y los
            # intentos de escritura de quien hubiera practicado esas
            # palabras, en silencio y en producción.
            #
            # Marcarlas como RETIRADO logra lo mismo de cara al usuario
            # (escena_get_publicada y progreso_resumen filtran por
            # PUBLICADO, así que desaparecen del recorrido y no cuentan para
            # los porcentajes) sin destruir nada. Y si una palabra vuelve al
            # temario, el update_or_create de abajo la repone en PUBLICADO
            # con su progreso histórico intacto, porque la fila nunca se fue.
            if options["purgar"]:
                progresos, intentos = _progreso_asociado(sobrantes)
                cuantas = sobrantes.count()
                if cuantas:
                    self.stdout.write(
                        self.style.WARNING(
                            f"--purgar: borrando {cuantas} objeto(s) de '{nombre_escena}' y, "
                            f"por cascada, {progresos} fila(s) de progreso y {intentos} "
                            f"intento(s) de escritura."
                        )
                    )
                sobrantes.delete()
            else:
                retiradas = sobrantes.exclude(estado=ObjetoInteractivo.Estado.RETIRADO).update(
                    estado=ObjetoInteractivo.Estado.RETIRADO
                )
                if retiradas:
                    self.stdout.write(
                        self.style.WARNING(
                            f"'{nombre_escena}': {retiradas} objeto(s) ya no están en el seed -- "
                            f"marcados como 'retirado' (no borrados, para no perder el progreso "
                            f"de los usuarios). Usa --purgar si de verdad quieres borrarlos."
                        )
                    )

            for i, (palabra, glosa_es, sprite_key) in enumerate(objetos):
                fila, columna = divmod(i, _GRID_COLS)
                # update_or_create (no get_or_create): sprite_key y otros campos
                # placeholder siguen ajustándose mientras se coordina con el
                # frontend, así que rehacer el seed debe corregir filas existentes.
                ObjetoInteractivo.objects.update_or_create(
                    escena=escena,
                    palabra=palabra,
                    defaults={
                        "lengua": lengua,
                        # glosa_es YA NO es igual a palabra. `palabra` es el slug
                        # sin acentos -- clave, nombre del audio, y lo que el alumno
                        # teclea con el teclado totonaco, que no tiene vocales
                        # acentuadas. `glosa_es` es la etiqueta que se muestra, con
                        # su ortografía real, y es por la que el frontend empareja
                        # cada punto con su objeto (resolveHotspot). Mientras los dos
                        # fueron el mismo slug, "sofá" y "mesa de centro" no
                        # emparejaban con nada: 8 de los 36 objetos sembrados eran
                        # invisibles para el recorrido sin que nada lo avisara.
                        "glosa_es": glosa_es,
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
        if options["con_progreso"]:
            self._sembrar_progreso(usuario)

        self.stdout.write(
            self.style.WARNING(
                "Las palabras sembradas son placeholders en español, NO traducciones "
                "reales al totonaco — reemplazar cuando llegue el contenido validado."
            )
        )

    def _sembrar_progreso(self, usuario):
        """Marca unos objetos como descubiertos y dominados para `usuario`.

        Pasa por los servicios reales de apps/progress en vez de crear filas a
        mano: así un intento marcado como correcto lo es porque el texto
        coincide de verdad con la palabra, y no por haber escrito
        `correcto=True` en una fila que no se sostiene. Idempotente: no apila
        intentos si ya hay progreso sembrado.
        """
        from apps.progress import services as progreso_services

        descubiertos = dominados = fallidos = 0

        for codigo, n_descubrir, n_dominar in _MUESTRA_PROGRESO:
            objetos = list(
                ObjetoInteractivo.objects.filter(
                    escena__codigo=codigo, estado=ObjetoInteractivo.Estado.PUBLICADO
                ).order_by("id")[:n_descubrir]
            )
            for i, objeto in enumerate(objetos):
                progreso_services.progreso_marcar_descubierto(usuario=usuario, objeto_id=objeto.id)
                descubiertos += 1

                if IntentoEscritura.objects.filter(usuario=usuario, objeto=objeto).exists():
                    continue  # ya sembrado: no apilar intentos al repetir

                if i < n_dominar:
                    # Correcto porque el texto coincide, no por decreto.
                    progreso_services.intento_escritura_registrar(
                        usuario=usuario, objeto_id=objeto.id, texto_ingresado=objeto.palabra
                    )
                    dominados += 1
                elif codigo == _ESCENA_INTENTO_FALLIDO and i == n_dominar:
                    progreso_services.intento_escritura_registrar(
                        usuario=usuario, objeto_id=objeto.id, texto_ingresado="(muestra de demo)"
                    )
                    fallidos += 1

        # Se informa del ESTADO RESULTANTE, no de lo que creó esta corrida.
        # En una base recién recreada --el caso para el que existe esto-- son
        # lo mismo, pero en una base de desarrollo con progreso acumulado de
        # antes no lo son, y decir "9 descubiertos" cuando la cuenta tiene 26
        # sería un informe engañoso aunque cada número fuera cierto por
        # separado.
        from apps.progress.selectors import progreso_resumen, progreso_total

        resumen = progreso_resumen(usuario=usuario)
        total = progreso_total(resumen_por_escena=resumen)
        escenas_tocadas = sum(1 for e in resumen if e["objetos_descubiertos"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Progreso de muestra sembrado para '{usuario.username}' "
                f"(+{descubiertos} descubierto(s), +{dominados} dominado(s), "
                f"+{fallidos} con último intento fallido en esta corrida)."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Estado resultante de la cuenta: {total['objetos_descubiertos']} de "
                f"{total['total_objetos']} objeto(s) descubierto(s) "
                f"({total['porcentaje']}%), {total['objetos_dominados']} dominado(s) "
                f"({total['porcentaje_dominado']}%), en {escenas_tocadas} de "
                f"{len(resumen)} escena(s)."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Es DATO DE DEMOSTRACIÓN, no uso medido: la muestra toca pocos objetos "
                "en 3 de 8 escenas y ninguna al 100%. Sirve para que la pantalla de "
                "progreso tenga algo que enseñar tras recrear la base; no para sostener "
                "ninguna afirmación. Si el estado resultante de arriba es mayor que la "
                "muestra, esta base ya traía progreso de antes."
            )
        )
