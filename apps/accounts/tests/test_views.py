import pytest
from django.core.cache import cache
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
        {"username": "aspirante_admin", "password": "ContraseñaSegura123", "rol": "admin"},
        format="json",
    )

    assert respuesta.status_code == 201
    usuario = Usuario.objects.get(username="aspirante_admin")
    assert usuario.rol == Usuario.Rol.APRENDIZ


def test_registro_rechaza_username_duplicado():
    UsuarioFactory(username="ya_existe")

    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "ya_existe", "password": "ContraseñaSegura123"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_registro_rechaza_password_debil():
    respuesta = APIClient().post(
        "/api/registro/",
        {"username": "alguien", "password": "123"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_usuario_registrado_puede_hacer_login_normal_despues():
    APIClient().post(
        "/api/registro/",
        {"username": "login_despues", "password": "ContraseñaSegura123"},
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
            {"username": f"limite_registro_{i}", "password": "ContraseñaSegura123"},
            format="json",
        )
        assert respuesta.status_code == 201

    respuesta = client.post(
        "/api/registro/",
        {"username": "limite_registro_extra", "password": "ContraseñaSegura123"},
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
