from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.models import Usuario
from apps.accounts.tests.factories import UsuarioFactory
from apps.accounts.views import (
    ConfirmarResetPasswordView,
    ConfirmarVerificacionEmailView,
    SolicitarResetPasswordView,
    SolicitarVerificacionEmailView,
)

pytestmark = pytest.mark.django_db


def con_topes(**tasas):
    """Fija las tasas de throttle SOLO para una prueba.

    Antes cada prueba repetia a mano el numero de produccion (un bucle de
    `range(10)` porque la tasa era 10/min), asi que cambiar la tasa rompia
    pruebas que no tenian nada que ver con lo que habia cambiado -- y
    peor: invitaba a ajustar el bucle en vez de pensar si el cambio
    estaba bien. Lo que estas pruebas comprueban es EL MECANISMO: que al
    pasarse del tope llega un 429. El numero lo pone la prueba.

    NO SIRVE `override_settings(REST_FRAMEWORK=...)`, y vale la pena
    saber por que: DRF liga las tasas a un ATRIBUTO DE CLASE en el
    momento de importar el modulo --

        class SimpleRateThrottle(BaseThrottle):
            THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    -- asi que cuando `override_settings` hace que `api_settings` se
    recargue, lo que obtiene es un dict NUEVO, y la clase sigue apuntando
    al viejo. Comprobado: con el override puesto, las cuatro pruebas
    devolvian 401 en vez de 429, o sea que el tope no se movia. Se
    parchea el atributo de la clase, que es lo que el throttle lee de
    verdad.
    """
    tope = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], **tasas}
    return mock.patch.object(SimpleRateThrottle, "THROTTLE_RATES", tope)


def por_minuto(scope):
    """Los intentos por minuto que concede un scope, segun la config real."""
    cantidad, periodo = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope].split("/")
    return int(cantidad) * {"min": 1, "hour": 1 / 60, "day": 1 / 1440}[periodo]


def test_registro_crea_usuario_y_devuelve_tokens():
    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "nueva_persona", "email": "nueva@example.com", "password": "ContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 201
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data
    assert respuesta.data["user"]["username"] == "nueva_persona"
    assert respuesta.data["user"]["rol"] == Usuario.Rol.APRENDIZ

    usuario = Usuario.objects.get(username="nueva_persona")
    assert usuario.check_password("ContraseñaSegura123")
    assert usuario.rol == Usuario.Rol.APRENDIZ


def test_registro_no_permite_elegir_rol():
    respuesta = APIClient().post(
        "/api/registro/",
        {
            "username": "aspirante_admin",
            "email": "aspirante_admin@example.com",
            "password": "ContraseñaSegura123",
            "rol": "admin",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    usuario = Usuario.objects.get(username="aspirante_admin")
    assert usuario.rol == Usuario.Rol.APRENDIZ


def test_registro_rechaza_username_duplicado():
    UsuarioFactory(username="ya_existe")

    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "ya_existe", "email": "otro@example.com", "password": "ContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_registro_rechaza_email_duplicado():
    UsuarioFactory(email="repetido@example.com")

    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "alguien_mas", "email": "repetido@example.com", "password": "ContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_registro_rechaza_sin_email():
    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "sin_correo", "password": "ContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "email" in respuesta.data


def test_registro_rechaza_password_debil():
    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "alguien", "email": "alguien@example.com", "password": "123"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_usuario_registrado_puede_hacer_login_normal_despues():
    APIClient().post(
        "/api/registro/",
        {"username": "login_despues", "email": "login_despues@example.com", "password": "ContraseñaSegura123"},
        format="json",
    )

    respuesta = APIClient().post(
        "/api/token/",
        {"username": "login_despues", "password": "ContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert "access" in respuesta.data


@con_topes(registro="3/min")
def test_registro_limita_intentos_por_minuto():
    cache.clear()
    client = APIClient()

    for i in range(3):
        respuesta = client.post(
            "/api/registro/",
            {"username": f"limite_registro_{i}", "email": f"limite_registro_{i}@example.com", "password": "ContraseñaSegura123"},
            format="json",
        )
        assert respuesta.status_code == 201

    respuesta = client.post(
        "/api/registro/",
        {"username": "limite_registro_extra", "email": "limite_registro_extra@example.com", "password": "ContraseñaSegura123"},
        format="json",
    )
    assert respuesta.status_code == 429


@con_topes(token_obtain="3/min")
def test_token_obtain_limita_intentos_por_ip():
    # Usa un username distinto en cada intento para que el throttle POR
    # CUENTA nunca se dispare — así se aísla el límite por IP del test de
    # más abajo.
    cache.clear()
    client = APIClient()

    for i in range(3):
        UsuarioFactory(username=f"limite_login_ip_{i}")
        respuesta = client.post(
            "/api/token/",
            {"username": f"limite_login_ip_{i}", "password": "contraseña-incorrecta"},
            format="json",
        )
        assert respuesta.status_code == 401

    UsuarioFactory(username="limite_login_ip_extra")
    respuesta = client.post(
        "/api/token/",
        {"username": "limite_login_ip_extra", "password": "contraseña-incorrecta"},
        format="json",
    )
    assert respuesta.status_code == 429


@con_topes(token_obtain_por_cuenta="3/min")
def test_token_obtain_limita_intentos_por_cuenta_aunque_la_ip_cambie():
    # Un atacante con muchas IPs distintas no debería tener tope infinito
    # contra UNA sola cuenta — cada intento aquí viene de una IP (X-Forwarded-
    # For) distinta, así que si esto se detiene es por PorCuentaScopedRateThrottle,
    # no por el throttle de IP.
    cache.clear()
    UsuarioFactory(username="limite_login_cuenta")
    client = APIClient()

    for i in range(3):
        respuesta = client.post(
            "/api/token/",
            {"username": "limite_login_cuenta", "password": "contraseña-incorrecta"},
            format="json",
            HTTP_X_FORWARDED_FOR=f"203.0.113.{i}",
        )
        assert respuesta.status_code == 401

    respuesta = client.post(
        "/api/token/",
        {"username": "limite_login_cuenta", "password": "contraseña-incorrecta"},
        format="json",
        HTTP_X_FORWARDED_FOR="203.0.113.99",
    )
    assert respuesta.status_code == 429


@con_topes(token_obtain="90/min", token_obtain_sostenido="3/hour")
def test_token_obtain_tiene_tambien_un_tope_por_hora():
    """El tope del minuto cubre la ráfaga de un salón; este acota el abuso.

    Se comprueba que está CONECTADO, que es lo que podría romperse sin que
    nadie se diera cuenta: si RealIpSostenidoScopedRateThrottle se cayera
    de la vista, o el nombre del scope dejara de coincidir, DRF no
    protesta — ScopedRateThrottle deja pasar la petición cuando la vista
    no declara su atributo. O sea que el límite desaparecería EN SILENCIO
    y las demás pruebas seguirían en verde.

    El tope por minuto se deja alto a propósito para que lo que detenga
    la cuarta petición sea el de la hora y no el otro.
    """
    cache.clear()
    client = APIClient()

    for i in range(3):
        UsuarioFactory(username=f"limite_hora_{i}")
        respuesta = client.post(
            "/api/token/",
            {"username": f"limite_hora_{i}", "password": "contraseña-incorrecta"},
            format="json",
        )
        assert respuesta.status_code == 401

    UsuarioFactory(username="limite_hora_extra")
    respuesta = client.post(
        "/api/token/",
        {"username": "limite_hora_extra", "password": "contraseña-incorrecta"},
        format="json",
    )
    assert respuesta.status_code == 429


def test_los_topes_por_ip_aguantan_un_salon_entero():
    """EL REQUISITO DEL CAMPO, ESCRITO COMO PRUEBA.

    Un salón entero sale por UNA sola IP pública: la de la escuela. La
    prueba de campo son varios grupos de 60+ alumnos que se registran y
    entran ahí mismo, así que un tope por IP por debajo de eso bloquea la
    prueba — y el síntoma, visto desde el salón, es "no les deja entrar",
    sin nada que apunte a la causa.

    Esto no mide código: fija el requisito para que bajar los topes sin
    querer (o "por seguridad", que es la tentación) falle aquí y no
    delante de un grupo.

    El de fuerza bruta de verdad es token_obtain_por_cuenta, y ese sigue
    estricto: cinco intentos por minuto contra una cuenta concreta, sin
    importar desde cuántas IPs vengan.
    """
    assert por_minuto("registro") >= 60
    assert por_minuto("token_obtain") >= 60
    # Y el sostenido tiene que dar para varios grupos en una mañana.
    assert por_minuto("registro_sostenido") * 60 >= 240
    assert por_minuto("token_obtain_sostenido") * 60 >= 240
    # Lo que NO debe relajarse al hacer sitio para el salón.
    assert por_minuto("token_obtain_por_cuenta") <= 5


def test_me_devuelve_datos_del_usuario_autenticado():
    usuario = UsuarioFactory(username="quien_soy", email="quien@example.com")
    client = APIClient()
    client.force_authenticate(user=usuario)

    respuesta = client.get("/api/me/")

    assert respuesta.status_code == 200
    assert respuesta.data["username"] == "quien_soy"
    assert respuesta.data["email"] == "quien@example.com"
    assert respuesta.data["rol"] == Usuario.Rol.APRENDIZ


def test_me_expone_si_el_correo_esta_verificado():
    # El frontend necesita este campo para decidir si enseña el boton de
    # "verificar correo" o la marca de "ya verificado" -- si desaparece de
    # aqui sin que nadie lo note, esa pantalla se queda sin dato para
    # decidir que mostrar.
    usuario = UsuarioFactory(email_verificado=False)
    client = APIClient()
    client.force_authenticate(user=usuario)

    respuesta = client.get("/api/me/")

    assert respuesta.data["email_verificado"] is False


def test_me_requiere_autenticacion():
    respuesta = APIClient().get("/api/me/")

    assert respuesta.status_code == 401


def test_token_refresh_rota_el_refresh_token():
    usuario = UsuarioFactory(username="rota_refresh")
    usuario.set_password("ContraseñaSegura123")
    usuario.save()

    login = APIClient().post(
        "/api/token/", {"username": "rota_refresh", "password": "ContraseñaSegura123"}, format="json"
    )
    refresh_original = login.data["refresh"]

    respuesta = APIClient().post("/api/token/refresh/", {"refresh": refresh_original}, format="json")

    assert respuesta.status_code == 200
    assert "refresh" in respuesta.data
    assert respuesta.data["refresh"] != refresh_original


def test_token_refresh_invalida_el_refresh_viejo_despues_de_usarlo():
    # Antes de ROTATE_REFRESH_TOKENS+BLACKLIST_AFTER_ROTATION, el mismo
    # refresh token servía indefinidamente hasta su expiración natural (7
    # días) sin importar cuántas veces se usara.
    usuario = UsuarioFactory(username="refresh_usado_dos_veces")
    usuario.set_password("ContraseñaSegura123")
    usuario.save()

    login = APIClient().post(
        "/api/token/",
        {"username": "refresh_usado_dos_veces", "password": "ContraseñaSegura123"},
        format="json",
    )
    refresh_original = login.data["refresh"]

    primer_uso = APIClient().post("/api/token/refresh/", {"refresh": refresh_original}, format="json")
    assert primer_uso.status_code == 200

    segundo_uso = APIClient().post("/api/token/refresh/", {"refresh": refresh_original}, format="json")
    assert segundo_uso.status_code == 401


def _uid_token_para(usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    return uid, token


def test_solicitar_reset_envia_correo_con_enlace_si_el_email_existe():
    # password_reset es un scope de throttle compartido por las 6 pruebas de
    # este bloque (ver test_restablecer_password_limita_intentos_por_minuto);
    # se limpia al inicio de cada una para que no se contaminen entre sí.
    cache.clear()
    usuario = UsuarioFactory(email="conoce@example.com")

    respuesta = APIClient().post(
        "/api/restablecer-password/", {"email": "conoce@example.com"}, format="json"
    )

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["conoce@example.com"]
    assert "restablecer-password?uid=" in mail.outbox[0].body
    assert f"uid={urlsafe_base64_encode(force_bytes(usuario.pk))}" in mail.outbox[0].body


def test_solicitar_reset_responde_igual_y_no_envia_correo_si_el_email_no_existe():
    cache.clear()
    respuesta = APIClient().post(
        "/api/restablecer-password/", {"email": "nadie@example.com"}, format="json"
    )

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 0


@con_topes(password_reset="90/min", envio_correo_sostenido="3/hour")
def test_solicitar_reset_tiene_tambien_un_tope_por_hora():
    """El de ráfaga (password_reset) no basta para proteger el cupo de
    Brevo: 5/min sostenido una hora entera ya son 300 correos, el cupo
    DIARIO gratis completo. Esta es la misma comprobación de conectividad
    que test_token_obtain_tiene_tambien_un_tope_por_hora -- que el scope
    sostenido este REALMENTE atado a la vista, no solo declarado en
    settings. Ver esa prueba para el por que de la mecánica.

    El tope por minuto se deja alto a propósito para que lo que detenga
    la cuarta petición sea el de la hora y no el otro.
    """
    cache.clear()

    for i in range(3):
        respuesta = APIClient().post(
            "/api/restablecer-password/", {"email": f"intento{i}@example.com"}, format="json"
        )
        assert respuesta.status_code == 200

    respuesta = APIClient().post(
        "/api/restablecer-password/", {"email": "intento-extra@example.com"}, format="json"
    )
    assert respuesta.status_code == 429


def test_confirmar_reset_no_lleva_el_sostenido_porque_no_manda_correo():
    """CONFIRMADO, NO SUPUESTO: confirmar no esta en el camino que gasta
    el cupo de Brevo -- no manda nada -- asi que no necesita el tope
    sostenido que si protege a SolicitarResetPasswordView. Si algun dia
    confirmar empezara a enviar algo -- un "tu contraseña cambio" por
    ejemplo -- esta prueba es la que habria que tocar primero."""
    assert not hasattr(ConfirmarResetPasswordView, "throttle_scope_sostenido")
    assert hasattr(SolicitarResetPasswordView, "throttle_scope_sostenido")


def test_el_sostenido_de_envio_de_correo_protege_el_cupo_diario_de_brevo():
    """EL REQUISITO, ESCRITO COMO PRUEBA -- en la direccion contraria a
    test_los_topes_por_ip_aguantan_un_salon_entero: ahi un tope bajo sin
    querer rompe una clase; aqui un tope ALTO sin querer deja agotar a
    Brevo.

    Brevo da 300 correos gratis AL DIA. Una sola IP sosteniendo el tope
    por hora las 24 horas -- en CUALQUIER COMBINACION de restablecer
    contraseña y verificar correo, porque las dos comparten este mismo
    scope -- no debe poder agotarlo sola. Con margen, porque un dia de
    clase no son 24 horas de abuso sostenido pero tampoco hay que apurar
    el limite al milimetro.
    """
    agotaria_en_un_dia = por_minuto("envio_correo_sostenido") * 60 * 24
    assert agotaria_en_un_dia < 300


def test_confirmar_reset_cambia_la_contrasena_con_token_valido():
    cache.clear()
    usuario = UsuarioFactory()
    uid, token = _uid_token_para(usuario)

    respuesta = APIClient().post(
        "/api/restablecer-password/confirmar/",
        {"uid": uid, "token": token, "password": "NuevaContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password("NuevaContraseñaSegura123")


def test_confirmar_reset_invalida_los_tokens_emitidos_antes_del_cambio():
    # Sin CHECK_REVOKE_TOKEN, una cuenta comprometida seguiría accesible con
    # el access/refresh token robado hasta su propia expiración (hasta 1h/7d
    # después) aunque el dueño ya haya restablecido su contraseña — este es
    # justo el escenario que CHECK_REVOKE_TOKEN (SIMPLE_JWT en settings.py)
    # cierra.
    cache.clear()
    usuario = UsuarioFactory(username="con_sesion_previa")
    usuario.set_password("defaultpassword123")
    usuario.save()

    login = APIClient().post(
        "/api/token/",
        {"username": "con_sesion_previa", "password": "defaultpassword123"},
        format="json",
    )
    access_previo = login.data["access"]

    # De verdad sirve antes del reset.
    respuesta_antes = APIClient().get(
        "/api/me/", HTTP_AUTHORIZATION=f"Bearer {access_previo}"
    )
    assert respuesta_antes.status_code == 200

    uid, token = _uid_token_para(usuario)
    APIClient().post(
        "/api/restablecer-password/confirmar/",
        {"uid": uid, "token": token, "password": "NuevaContraseñaSegura123"},
        format="json",
    )

    respuesta_despues = APIClient().get(
        "/api/me/", HTTP_AUTHORIZATION=f"Bearer {access_previo}"
    )
    assert respuesta_despues.status_code == 401


def test_confirmar_reset_rechaza_token_invalido():
    cache.clear()
    usuario = UsuarioFactory()
    uid, _ = _uid_token_para(usuario)

    respuesta = APIClient().post(
        "/api/restablecer-password/confirmar/",
        {"uid": uid, "token": "token-invalido", "password": "NuevaContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 400
    usuario.refresh_from_db()
    assert not usuario.check_password("NuevaContraseñaSegura123")


def test_confirmar_reset_rechaza_token_ya_usado():
    cache.clear()
    usuario = UsuarioFactory()
    uid, token = _uid_token_para(usuario)
    client = APIClient()

    primera = client.post(
        "/api/restablecer-password/confirmar/",
        {"uid": uid, "token": token, "password": "PrimeraContraseña123"},
        format="json",
    )
    assert primera.status_code == 200

    # El token de Django incorpora el hash de contraseña vigente: al haber
    # cambiado, el mismo token ya no es válido para un segundo uso.
    segunda = client.post(
        "/api/restablecer-password/confirmar/",
        {"uid": uid, "token": token, "password": "SegundaContraseña456"},
        format="json",
    )
    assert segunda.status_code == 400


def test_confirmar_reset_rechaza_password_debil():
    cache.clear()
    usuario = UsuarioFactory()
    uid, token = _uid_token_para(usuario)

    respuesta = APIClient().post(
        "/api/restablecer-password/confirmar/",
        {"uid": uid, "token": token, "password": "123"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_restablecer_password_limita_intentos_por_minuto():
    cache.clear()
    client = APIClient()

    for _ in range(5):
        respuesta = client.post(
            "/api/restablecer-password/", {"email": "quien-sea@example.com"}, format="json"
        )
        assert respuesta.status_code == 200

    respuesta = client.post(
        "/api/restablecer-password/", {"email": "quien-sea@example.com"}, format="json"
    )
    assert respuesta.status_code == 429


def _autenticado(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


def test_solicitar_verificacion_requiere_sesion():
    cache.clear()
    respuesta = APIClient().post("/api/verificar-email/", {}, format="json")
    assert respuesta.status_code == 401


def test_solicitar_verificacion_envia_codigo_de_seis_digitos():
    cache.clear()
    usuario = UsuarioFactory(email="aprende@example.com")

    respuesta = _autenticado(usuario).post("/api/verificar-email/", {}, format="json")

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["aprende@example.com"]
    codigo = usuario.codigos_verificacion_email.get().codigo
    assert len(codigo) == 6
    assert codigo.isdigit()
    assert codigo in mail.outbox[0].body


def test_solicitar_verificacion_no_reenvia_si_ya_esta_verificado():
    # No es solo cortesia: cada reenvio gasta un correo real del mismo
    # cupo de Brevo que protege envio_correo_sostenido. Pedirlo de nuevo
    # cuando ya no hace falta no deberia costar nada.
    cache.clear()
    usuario = UsuarioFactory(email_verificado=True)

    respuesta = _autenticado(usuario).post("/api/verificar-email/", {}, format="json")

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 0


def test_solicitar_verificacion_invalida_el_codigo_anterior():
    # Pedir un codigo nuevo no debe dejar vivo al anterior -- si alguien
    # vio el correo viejo (un buzon compartido, un reenvio de puro accidente)
    # no debe poder usarlo despues de que se pidio otro.
    cache.clear()
    usuario = UsuarioFactory()
    _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
    viejo = usuario.codigos_verificacion_email.get().codigo

    _autenticado(usuario).post("/api/verificar-email/", {}, format="json")

    assert not usuario.codigos_verificacion_email.filter(codigo=viejo).exists()


def test_confirmar_verificacion_requiere_sesion():
    cache.clear()
    respuesta = APIClient().post("/api/verificar-email/confirmar/", {"codigo": "123456"}, format="json")
    assert respuesta.status_code == 401


def test_confirmar_verificacion_con_codigo_correcto_marca_verificado():
    cache.clear()
    usuario = UsuarioFactory()
    _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
    codigo = usuario.codigos_verificacion_email.get().codigo

    respuesta = _autenticado(usuario).post(
        "/api/verificar-email/confirmar/", {"codigo": codigo}, format="json"
    )

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.email_verificado is True


def test_confirmar_verificacion_consume_el_codigo_tras_usarlo():
    cache.clear()
    usuario = UsuarioFactory()
    _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
    codigo = usuario.codigos_verificacion_email.get().codigo
    cliente = _autenticado(usuario)

    primera = cliente.post("/api/verificar-email/confirmar/", {"codigo": codigo}, format="json")
    segunda = cliente.post("/api/verificar-email/confirmar/", {"codigo": codigo}, format="json")

    assert primera.status_code == 200
    assert segunda.status_code == 400


def test_confirmar_verificacion_con_codigo_incorrecto_no_verifica():
    cache.clear()
    usuario = UsuarioFactory()
    _autenticado(usuario).post("/api/verificar-email/", {}, format="json")

    respuesta = _autenticado(usuario).post(
        "/api/verificar-email/confirmar/", {"codigo": "000000"}, format="json"
    )

    assert respuesta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.email_verificado is False


def test_confirmar_verificacion_con_codigo_caducado_no_verifica():
    from datetime import timedelta

    from django.utils import timezone

    cache.clear()
    usuario = UsuarioFactory()
    _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
    codigo = usuario.codigos_verificacion_email.get()
    # Se adelanta el reloj del propio codigo en vez de esperar de verdad
    # 15 minutos: `creado` es auto_now_add (solo se fija al crear), asi
    # que un update() posterior si puede moverlo.
    usuario.codigos_verificacion_email.filter(pk=codigo.pk).update(
        creado=timezone.now() - timedelta(minutes=16)
    )

    respuesta = _autenticado(usuario).post(
        "/api/verificar-email/confirmar/", {"codigo": codigo.codigo}, format="json"
    )

    assert respuesta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.email_verificado is False


def test_confirmar_verificacion_no_distingue_un_codigo_que_no_es_del_otro(django_assert_num_queries):
    # El codigo de UN usuario no debe servir para verificar la cuenta de
    # OTRO, aunque alguien lo adivine o lo intercepte: confirmar siempre
    # busca dentro de los codigos de `request.user`, nunca de la tabla
    # entera.
    cache.clear()
    uno = UsuarioFactory()
    otro = UsuarioFactory()
    _autenticado(uno).post("/api/verificar-email/", {}, format="json")
    codigo_de_uno = uno.codigos_verificacion_email.get().codigo

    respuesta = _autenticado(otro).post(
        "/api/verificar-email/confirmar/", {"codigo": codigo_de_uno}, format="json"
    )

    assert respuesta.status_code == 400
    otro.refresh_from_db()
    assert otro.email_verificado is False


@con_topes(verificar_email="90/min", envio_correo_sostenido="3/hour")
def test_solicitar_verificacion_tiene_tambien_un_tope_por_hora():
    """Misma mecanica que test_solicitar_reset_tiene_tambien_un_tope_por_hora:
    comprobar que el scope sostenido esta REALMENTE atado a esta vista."""
    cache.clear()

    for i in range(3):
        usuario = UsuarioFactory(username=f"verificar_{i}")
        respuesta = _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
        assert respuesta.status_code == 200

    extra = UsuarioFactory(username="verificar_extra")
    respuesta = _autenticado(extra).post("/api/verificar-email/", {}, format="json")
    assert respuesta.status_code == 429


@con_topes(password_reset="90/min", verificar_email="90/min", envio_correo_sostenido="3/hour")
def test_restablecer_y_verificar_comparten_el_mismo_cupo_sostenido():
    """EL REQUISITO DE FONDO de compartir el scope, escrito como prueba:
    si algun dia alguien le diera a cada vista su PROPIO scope sostenido
    -- por prolijidad, sin pensarlo -- esta prueba es la que lo cazaria.
    Dos peticiones a restablecer-password y una a verificar-email deben
    agotar el MISMO tope de 3/hour, no tres topes independientes."""
    cache.clear()
    usuario = UsuarioFactory(email="comparte@example.com")

    r1 = APIClient().post(
        "/api/restablecer-password/", {"email": "comparte@example.com"}, format="json"
    )
    r2 = APIClient().post(
        "/api/restablecer-password/", {"email": "comparte@example.com"}, format="json"
    )
    r3 = _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
    assert [r1.status_code, r2.status_code, r3.status_code] == [200, 200, 200]

    # La cuarta, sea de la vista que sea, ya se topa con el mismo scope.
    r4 = _autenticado(usuario).post("/api/verificar-email/", {}, format="json")
    assert r4.status_code == 429


def test_confirmar_verificacion_no_lleva_el_sostenido_porque_no_manda_correo():
    assert not hasattr(ConfirmarVerificacionEmailView, "throttle_scope_sostenido")
    assert hasattr(SolicitarVerificacionEmailView, "throttle_scope_sostenido")
