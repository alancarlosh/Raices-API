"""Devuelve a la base lo que `respaldar` guardó.

UN RESPALDO QUE NADIE HA RESTAURADO NO ES UN RESPALDO. Por eso este
comando existe desde el mismo día que el otro y no "cuando haga falta",
y por eso hay una prueba que hace el viaje de ida y vuelta completo
(apps/accounts/tests/test_respaldo.py): respalda, borra, restaura y
compara. El día 30 de noviembre no es el momento de descubrir que el
formato no cargaba.

ORDEN Y COLISIONES. Se carga con el orden del archivo, que `respaldar`
ya emite con los usuarios primero para que las claves ajenas resuelvan.
Las filas se guardan con su PK original, así que restaurar sobre una
base que ya tenga datos SOBRESCRIBE esas filas. Es lo correcto para el
caso real -- base nueva y vacía tras la caducidad -- pero convierte un
error de dedo en pérdida de datos, así que hace falta --si-de-verdad.

LO QUE NO HACE: tocar el catálogo. Las claves ajenas de progreso e
intentos apuntan a ObjetoInteractivo POR ID, así que la base destino
tiene que tener el catálogo ya sembrado y con los mismos ids. En Render
eso ocurre solo: `seed_demo` corre en cada despliegue, antes que esto.
Si los ids no coinciden, el comando lo dice y no escribe nada.
"""
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content.models import ObjetoInteractivo


class Command(BaseCommand):
    help = "Restaura un respaldo hecho con `respaldar`. Sobrescribe por PK."

    def add_arguments(self, parser):
        parser.add_argument("archivo")
        parser.add_argument(
            "--si-de-verdad",
            action="store_true",
            help="Confirma que quieres sobrescribir filas por PK.",
        )

    def handle(self, *args, **opciones):
        if not opciones["si_de_verdad"]:
            raise CommandError(
                "Esto sobrescribe filas por su clave primaria. Si la base "
                "destino no está vacía, perderás lo que haya. Repite con "
                "--si-de-verdad cuando lo tengas claro."
            )

        with open(opciones["archivo"], encoding="utf-8") as f:
            crudo = f.read()

        objetos = list(serializers.deserialize("json", crudo))
        if not objetos:
            raise CommandError("El respaldo está vacío.")

        # COMPROBAR ANTES DE ESCRIBIR. Si el catálogo de la base destino no
        # tiene los ids que el respaldo referencia, la carga fallaría a
        # medias y dejaría la base en un estado peor que antes.
        faltan = set()
        for obj in objetos:
            objeto_id = getattr(obj.object, "objeto_id", None)
            if objeto_id is not None:
                faltan.add(objeto_id)
        if faltan:
            existen = set(
                ObjetoInteractivo.objects.filter(id__in=faltan)
                .values_list("id", flat=True)
            )
            perdidos = sorted(faltan - existen)
            if perdidos:
                raise CommandError(
                    f"El catálogo de esta base no tiene {len(perdidos)} de "
                    f"los objetos que el respaldo referencia (ids "
                    f"{perdidos[:8]}{'...' if len(perdidos) > 8 else ''}). "
                    "Siembra el catálogo primero (seed_demo) y repite. No "
                    "se escribió nada."
                )

        cuenta = {}
        with transaction.atomic():
            for obj in objetos:
                obj.save()
                nombre = type(obj.object).__name__
                cuenta[nombre] = cuenta.get(nombre, 0) + 1

        for nombre, n in sorted(cuenta.items()):
            self.stdout.write(f"  {nombre:24s} {n:5d}")
        self.stdout.write(self.style.SUCCESS(
            f"RESTAURADO {sum(cuenta.values())} filas"
        ))
