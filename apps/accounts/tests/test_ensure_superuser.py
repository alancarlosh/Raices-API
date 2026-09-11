import pytest
from django.core.management import call_command

from apps.accounts.models import Usuario

pytestmark = pytest.mark.django_db


def test_ensure_superuser_crea_admin_desde_env_vars(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin_render")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "ClaveDeAdminSegura123")
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

    call_command("ensure_superuser")

    usuario = Usuario.objects.get(username="admin_render")
    assert usuario.is_superuser
    assert usuario.is_staff
    assert usuario.rol == Usuario.Rol.ADMIN
    assert usuario.check_password("ClaveDeAdminSegura123")


def test_ensure_superuser_es_idempotente_y_actualiza_password(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin_render")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "PrimeraClave123")
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    call_command("ensure_superuser")

    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "SegundaClave456")
    call_command("ensure_superuser")

    assert Usuario.objects.filter(username="admin_render").count() == 1
    usuario = Usuario.objects.get(username="admin_render")
    assert usuario.check_password("SegundaClave456")


def test_ensure_superuser_no_hace_nada_sin_env_vars(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    call_command("ensure_superuser")

    assert Usuario.objects.count() == 0
