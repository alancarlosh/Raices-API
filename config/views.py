"""Vistas que no pertenecen a ninguna app de contenido: viven aqui."""
from django.http import JsonResponse


def salud(request):
    """GET /api/salud/ -- no hace nada mas que responder 200.

    Existe para DESPERTAR el servicio de Render sin esperar a que el
    alumno termine de escribir sus credenciales. El plan gratuito duerme
    el servicio tras 15 min sin trafico y tarda ~30 s en despertar (ver
    services/coldStart.ts en Raices-Front); sin esto, esos 30 s se le
    cobraban al PRIMER request real -- el login -- y el alumno los veia
    como una pantalla congelada despues de pulsar "Entrar".

    Raices-Front la llama en cuanto carga la pantalla de acceso, antes
    de que haya credenciales que mandar: con que el alumno tarde unos
    segundos en escribir su usuario y contraseña, el servicio ya esta
    despierto para cuando de verdad llega el POST a /api/token/.

    SIN BASE DE DATOS A PROPOSITO. Lo unico que hace falta despertar es
    el PROCESO de Django -- el servicio web es lo que Render suspende
    tras 15 min inactivo. Postgres en el plan gratuito de Render no se
    suspende de la misma forma por inactividad, asi que tocar la base
    de datos aqui solo gastaria una conexion de mas en cada carga de
    pantalla sin despertar nada que lo necesite.

    SIN AUTENTICAR Y SIN LIMITE DE PETICIONES, a proposito: es el unico
    endpoint que un visitante sin sesion necesita poder llamar antes de
    que exista ninguna credencial, y no hay nada que proteger -- no lee
    ni escribe nada, asi que no hay abuso que limitar.
    """
    return JsonResponse({"ok": True})
