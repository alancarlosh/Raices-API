"""Comprueba que TODAS las filas del respaldo estan en la base, una por una.

NO COMPARA TOTALES, Y ESA ES LA DIFERENCIA. `seed_demo` siembra el catalogo
y una cuenta demo, asi que la base del ensayo no parte de cero: un conteo
por diferencia podria cuadrar aunque faltaran filas, o no cuadrar aunque
estuvieran todas (restaurar sobrescribe POR CLAVE PRIMARIA, asi que una
fila del respaldo que choque con la cuenta sembrada pisa en vez de sumar).

Lo que se comprueba es lo unico que de verdad importa el dia que haya que
restaurar: que cada clave primaria que estaba en el archivo exista en la
base al terminar.

NO IMPRIME NADA PERSONAL. El respaldo lleva correos y hashes de
contrasena de alumnos reales; de aqui solo salen nombres de modelo,
cuentas y claves primarias numericas.
"""

import collections
import json
import os
import sys
from pathlib import Path

# La raiz del proyecto al path: al ejecutar este archivo directamente, python
# solo pone scripts/ en sys.path, asi que `config` y `apps` no se encuentran.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.accounts.models import Usuario  # noqa: E402
from apps.progress.models import IntentoEscritura, ProgresoUsuario  # noqa: E402
from apps.telemetria.models import MedicionRendimiento  # noqa: E402

MODELOS = [Usuario, ProgresoUsuario, IntentoEscritura, MedicionRendimiento]
POR_ETIQUETA = {m._meta.label_lower: m for m in MODELOS}


def main(ruta):
    with open(ruta, encoding="utf-8") as f:
        filas = json.load(f)

    esperadas = collections.defaultdict(set)
    desconocidos = collections.Counter()
    for fila in filas:
        etiqueta = fila["model"].lower()
        if etiqueta in POR_ETIQUETA:
            esperadas[etiqueta].add(fila["pk"])
        else:
            desconocidos[etiqueta] += 1

    print(f"  respaldo: {len(filas)} filas")
    problemas = []

    if desconocidos:
        # No es necesariamente un fallo -- el respaldo podria traer un
        # modelo nuevo -- pero hay que verlo, no que pase callando.
        for etiqueta, n in sorted(desconocidos.items()):
            print(f"    AVISO modelo no previsto: {etiqueta} ({n} filas)")

    print()
    print(f"  {'modelo':32s} {'respaldo':>9s} {'en la base':>11s}  resultado")
    for etiqueta, modelo in POR_ETIQUETA.items():
        quiero = esperadas.get(etiqueta, set())
        if not quiero:
            print(f"  {etiqueta:32s} {0:9d} {'-':>11s}  (no venia en el respaldo)")
            continue
        hay = set(modelo.objects.filter(pk__in=quiero).values_list("pk", flat=True))
        faltan = quiero - hay
        estado = "bien" if not faltan else f"FALTAN {len(faltan)}"
        print(f"  {etiqueta:32s} {len(quiero):9d} {len(hay):11d}  {estado}")
        if faltan:
            muestra = sorted(faltan)[:8]
            print(f"    claves que no llegaron: {muestra}"
                  f"{'...' if len(faltan) > 8 else ''}")
            problemas.append(etiqueta)

    print()
    if problemas:
        print(f"  ENSAYO FALLIDO: faltan filas en {', '.join(problemas)}")
        return 1
    if not esperadas:
        print("  ENSAYO FALLIDO: el respaldo no traia ninguna fila conocida.")
        return 1
    print("  ENSAYO CORRECTO: todas las filas del respaldo estan en la base.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("uso: verificar_restauracion.py <respaldo.json>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
