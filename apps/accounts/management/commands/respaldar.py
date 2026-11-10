"""Respalda lo que la base de datos NO puede regenerar sola.

POR QUÉ EXISTE, con fecha. La base de Render es del plan gratuito y se
BORRA a los 30 días; la próxima caducidad es el 30 de noviembre de 2026.
Ya pasó una vez, el 28 de octubre, y entonces no dolió: el catálogo —
escenas, objetos, palabras, audios — lo vuelve a sembrar `seed_demo` en
cada despliegue, así que se restauró solo.

Lo que NO se restaura solo es todo lo demás, y es justo lo que vale:

  - las CUENTAS de los alumnos (11 el 2026-11-09, y subiendo),
  - su PROGRESO y sus INTENTOS DE ESCRITURA,
  - las MEDICIONES DE RENDIMIENTO.

Las dos últimas son la evidencia del capítulo de resultados de la tesis:
cuántos cuadros por segundo dio cada equipo real, qué palabras se
intentaron y cuáles se acertaron. Eso no se puede volver a generar — hay
que volver a reunir a los alumnos.

QUÉ NO RESPALDA, a propósito: nada del catálogo. Si se respaldara,
restaurar pisaría lo que `seed_demo` acabe de sembrar y se volvería a
una versión vieja del temario sin que nadie lo note. El catálogo tiene
su fuente de verdad en el repositorio, y esa es la correcta.

CONTIENE DATOS PERSONALES: nombres de usuario, correos y hashes de
contraseña. El archivo que genera NO debe subirse al repositorio ni
pasar por chat. Está en .gitignore y el comando lo avisa al terminar.
"""
import os

from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError

from apps.progress.models import IntentoEscritura, ProgresoUsuario
from apps.telemetria.models import MedicionRendimiento

Usuario = get_user_model()

# El orden IMPORTA al restaurar: las claves ajenas de progreso, intentos y
# mediciones apuntan a usuario, así que los usuarios van primero.
MODELOS = [Usuario, ProgresoUsuario, IntentoEscritura, MedicionRendimiento]


class Command(BaseCommand):
    help = (
        "Guarda cuentas, progreso, intentos de escritura y mediciones de "
        "rendimiento en un JSON. NO incluye el catálogo: eso lo siembra "
        "seed_demo desde el repositorio."
    )

    def add_arguments(self, parser):
        parser.add_argument("--salida", default="respaldo_raices.json")
        parser.add_argument(
            "--sin-cuentas",
            action="store_true",
            help=(
                "Omite los usuarios. El respaldo deja de servir para "
                "restaurar (las claves ajenas no resolverían) pero no "
                "lleva datos personales: sirve para analizar la telemetría "
                "fuera del servidor."
            ),
        )

    def handle(self, *args, **opciones):
        salida = opciones["salida"]
        modelos = MODELOS[1:] if opciones["sin_cuentas"] else MODELOS

        objetos = []
        resumen = []
        for modelo in modelos:
            filas = list(modelo.objects.all())
            objetos.extend(filas)
            resumen.append((modelo.__name__, len(filas)))

        if not objetos:
            raise CommandError(
                "No hay NADA que respaldar. Si esto corre contra la base de "
                "producción, es una señal de alarma, no un caso normal."
            )

        with open(salida, "w", encoding="utf-8") as f:
            serializers.serialize("json", objetos, stream=f, indent=1)

        for nombre, n in resumen:
            self.stdout.write(f"  {nombre:24s} {n:5d}")
        tam = os.path.getsize(salida) / 1024
        self.stdout.write(self.style.SUCCESS(
            f"RESPALDO {salida} ({tam:.0f} KB, {len(objetos)} filas)"
        ))
        if not opciones["sin_cuentas"]:
            self.stdout.write(self.style.WARNING(
                "Lleva datos personales (correos y hashes de contraseña): "
                "no lo subas al repositorio ni lo pases por chat."
            ))
