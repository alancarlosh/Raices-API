#!/usr/bin/env bash
#
# DESPERTAR LA API ANTES DE LA CLASE.
#
# El plan gratuito de Render apaga el servicio tras un rato sin visitas, y
# volver a encenderlo cuesta tiempo. MEDIDO en produccion:
#
#     primera peticion (dormido)   34 s
#     siguientes (despierto)        2 s
#
# Esos 34 s se los come el PRIMER alumno que entre, que ademas no sabe
# que esta esperando un arranque: ve la app colgada. Y como la API es de
# donde salen las escenas, ese arranque bloquea tambien al resto hasta
# que termina.
#
# Correr esto cinco minutos antes de la clase se lleva el problema
# entero, gratis:
#
#     ./scripts/calentar.sh
#
# POR QUE NO SE DEJA ENCENDIDA CON UN CRON. Seria lo obvio y es mala
# idea: el plan gratuito da 750 horas de instancia al mes y un mes tiene
# 720, asi que mantenerla despierta todo el dia consumiria practicamente
# toda la cuota, y se apagaria sola a final de mes -- probablemente el
# dia que haga falta. El apagado por inactividad es lo que hace que la
# cuota alcance. Mejor despertarla a mano cuando se sabe que hay clase.
#
# Despues de esto conviene esperar a que acaben los alumnos ESCALONADOS:
# la API atiende una peticion a la vez y cada registro cuesta ~1 s de CPU
# (ver apps/accounts/hashers.py), asi que 60 alumnos de golpe hacen cola.
# En grupos de diez son unos diez segundos por grupo.

set -u

API="${1:-https://raices-api.onrender.com}"
# SE EXIGE UNA RESPUESTA QUE SOLO PUEDE DAR ESTA API, no solo que algo
# contestara rapido. La primera version pedia una ruta inexistente y se
# quedaba con el tiempo: contra un dominio equivocado decia "despierta"
# igual, porque el borde de Render tambien contesta 404 en milisegundos y
# por el tiempo no se distingue de un 404 de Django.
#
# /api/escenas/ sin credenciales devuelve 401, y eso solo lo puede decir
# Django con DRF y las rutas cargadas. Ademas solo lee: no crea ni cambia
# nada, que es lo que se quiere de algo que se corre a ciegas antes de
# una clase.
RUTA="/api/escenas/"
ESPERADO="401"
DESPIERTA_SI_BAJA_DE=1.0
INTENTOS=10

printf 'Despertando %s\n\n' "$API"

for i in $(seq 1 "$INTENTOS"); do
    respuesta=$(curl -s -o /dev/null -w '%{time_total} %{http_code}' \
                     --max-time 120 "$API$RUTA" || echo "999 000")
    t=${respuesta% *}
    codigo=${respuesta#* }
    printf '  intento %-2s  %6.2f s  http=%s\n' "$i" "$t" "$codigo"

    if [ "$codigo" != "$ESPERADO" ]; then
        printf '      (se esperaba http=%s; puede estar arrancando o desplegando)\n' "$ESPERADO"
    elif awk "BEGIN{exit !($t < $DESPIERTA_SI_BAJA_DE)}"; then
        printf '\nDespierta. Ya pueden entrar los alumnos (en grupos de diez).\n'
        exit 0
    fi
done

printf '\nSigue lenta tras %s intentos. Puede estar desplegando: mira el panel\n' "$INTENTOS"
printf 'de Render antes de empezar la clase.\n'
exit 1
