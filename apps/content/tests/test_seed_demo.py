import pytest
from django.core.management import call_command

from apps.accounts.models import Usuario
from apps.content.models import Escena, ObjetoInteractivo

pytestmark = pytest.mark.django_db


def test_seed_demo_crea_escenas_objetos_y_usuario():
    call_command("seed_demo")

    assert Escena.objects.count() == 2
    assert ObjetoInteractivo.objects.filter(estado=ObjetoInteractivo.Estado.PUBLICADO).count() == 16
    usuario = Usuario.objects.get(username="demo")
    assert usuario.check_password("Demo12345!")


def test_seed_demo_es_idempotente():
    call_command("seed_demo")
    call_command("seed_demo")

    assert Escena.objects.count() == 2
    assert ObjetoInteractivo.objects.count() == 16
    assert Usuario.objects.filter(username="demo").count() == 1
