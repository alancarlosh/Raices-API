import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.accounts.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


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


def test_registro_limita_intentos_por_minuto():
    cache.clear()
    client = APIClient()

    for i in range(10):
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


def test_token_obtain_limita_intentos_por_minuto():
    cache.clear()
    UsuarioFactory(username="limite_login")
    client = APIClient()

    for _ in range(10):
        respuesta = client.post(
            "/api/token/",
            {"username": "limite_login", "password": "contraseña-incorrecta"},
            format="json",
        )
        assert respuesta.status_code == 401

    respuesta = client.post(
        "/api/token/",
        {"username": "limite_login", "password": "contraseña-incorrecta"},
        format="json",
    )
    assert respuesta.status_code == 429


def test_me_devuelve_datos_del_usuario_autenticado():
    usuario = UsuarioFactory(username="quien_soy", email="quien@example.com")
    client = APIClient()
    client.force_authenticate(user=usuario)

    respuesta = client.get("/api/me/")

    assert respuesta.status_code == 200
    assert respuesta.data["username"] == "quien_soy"
    assert respuesta.data["email"] == "quien@example.com"
    assert respuesta.data["rol"] == Usuario.Rol.APRENDIZ


def test_me_requiere_autenticacion():
    respuesta = APIClient().get("/api/me/")

    assert respuesta.status_code == 401


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
