#!/usr/bin/env bash
#
# ENSAYAR LA RESTAURACION CONTRA UNA BASE DESECHABLE.
#
#     ./scripts/ensayar_restauracion.sh respaldo_raices.json
#
# POR QUE EXISTE. La base de Render es del plan gratuito y se borra a los
# 30 dias (la proxima caducidad: 30 de noviembre de 2026). Lo que se
# pierde no es el catalogo -- ese lo vuelve a sembrar seed_demo en cada
# despliegue -- sino las cuentas de los alumnos, su progreso, sus intentos
# de escritura y las mediciones de rendimiento: la evidencia del capitulo
# de resultados, que no se regenera sin volver a reunir a los alumnos.
#
# Hay una prueba automatica que hace el viaje completo con datos de
# fabrica, y esta bien, pero no es lo mismo: lo que puede fallar el dia 30
# es EL ARCHIVO DE VERDAD, con los datos de verdad. Esto lo prueba con el
# archivo que se va a usar.
#
# NO TOCA NI PRODUCCION NI TU db.sqlite3. Monta una base SQLite nueva en
# un directorio temporal, trabaja ahi y la borra al salir. Si falla algo,
# lo unico que se pierde es el temporal.
#
# NO IMPRIME NADA PERSONAL. El respaldo lleva correos y hashes de
# contrasena de alumnos reales; de aqui solo salen nombres de modelo,
# cuentas y claves primarias.
#
# EL LIMITE DE ESTE ENSAYO, DICHO EN CLARO: produccion es Postgres y esto
# corre en SQLite, porque en esta maquina no hay ni Postgres ni Docker.
# El viaje de ida y vuelta de los datos SI se comprueba de verdad; lo que
# este ensayo NO puede descartar son los fallos propios de Postgres --
# secuencias de claves que quedan desfasadas tras escribir por PK, tipos
# que SQLite acepta y Postgres no, el orden en que se validan las
# restricciones. Para cubrir eso haria falta un Postgres local (brew
# install postgresql, o un contenedor) y volver a correr esto con
# DATABASE_URL apuntando a el: el script lo acepta tal cual.

set -euo pipefail

cd "$(dirname "$0")/.."

ARCHIVO="${1:-respaldo_raices.json}"
PY="./venv/bin/python"

if [ ! -f "$ARCHIVO" ]; then
    printf 'No encuentro el respaldo: %s\n\n' "$ARCHIVO" >&2
    printf 'Generalo primero contra produccion (la URL NO se guarda aqui):\n' >&2
    printf '  DATABASE_URL=... %s manage.py respaldar\n' "$PY" >&2
    exit 2
fi

if [ ! -x "$PY" ]; then
    printf 'No encuentro el interprete del entorno: %s\n' "$PY" >&2
    printf 'Crealo con: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt\n' >&2
    exit 2
fi

TMP="$(mktemp -d)"
# Se borra pase lo que pase: el temporal lleva una copia de los datos de
# los alumnos, asi que no se queda tirado por el disco.
trap 'rm -rf "$TMP"' EXIT

# La base del ensayo. settings.py lee DATABASE_URL (dj_database_url) y solo
# cae en db.sqlite3 cuando no esta puesta, asi que basta exportarla para
# que TODO lo de abajo trabaje en la desechable.
export DATABASE_URL="sqlite:///$TMP/ensayo.sqlite3"
export SECRET_KEY="${SECRET_KEY:-ensayo-local-no-secreta}"
export DEBUG="${DEBUG:-False}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-127.0.0.1}"
export DJANGO_SETTINGS_MODULE=config.settings

printf 'Ensayando la restauracion de %s\n' "$ARCHIVO"
printf 'Base desechable: %s\n' "$DATABASE_URL"
printf '(produccion es Postgres y esto es SQLite -- ver la nota de arriba)\n\n'

printf '1. Creando las tablas\n'
$PY manage.py migrate --noinput >/dev/null

printf '2. Sembrando el catalogo (restaurar lo exige: comprueba que los\n'
printf '   objetos que el respaldo referencia existan antes de escribir)\n'
$PY manage.py seed_demo >/dev/null

printf '3. Lo que hay ANTES de restaurar, para saber de donde se parte\n'
printf '   (el usuario demo lo siembra seed_demo: no es que la base venga\n'
printf '   sucia. Por eso el paso 5 compara CLAVE POR CLAVE y no totales:\n'
printf '   restaurar sobrescribe por clave primaria, asi que una cuenta del\n'
printf '   respaldo que choque con la sembrada pisa en vez de sumar, y un\n'
printf '   conteo por diferencia podria cuadrar faltando filas)\n'
$PY manage.py shell -c "
from apps.accounts.models import Usuario
from apps.progress.models import IntentoEscritura, ProgresoUsuario
from apps.telemetria.models import MedicionRendimiento
for m in (Usuario, ProgresoUsuario, IntentoEscritura, MedicionRendimiento):
    print(f'     {m._meta.label_lower:32s} {m.objects.count():5d}')
"

printf '\n4. Restaurando\n'
$PY manage.py restaurar "$ARCHIVO" --si-de-verdad

printf '\n5. Comprobando fila por fila\n'
$PY scripts/verificar_restauracion.py "$ARCHIVO"
