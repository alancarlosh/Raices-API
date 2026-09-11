import pytest
from django.core.management import call_command

from apps.accounts.models import Usuario
from apps.content.models import Escena, ObjetoInteractivo
from apps.content.seed_data import ESCENAS_SEED

TOTAL_ESCENAS = len(ESCENAS_SEED)
TOTAL_OBJETOS = sum(len(datos["objetos"]) for datos in ESCENAS_SEED.values())

pytestmark = pytest.mark.django_db


def test_seed_demo_crea_escenas_objetos_y_usuario():
    call_command("seed_demo")

    assert Escena.objects.count() == TOTAL_ESCENAS
    assert ObjetoInteractivo.objects.filter(estado=ObjetoInteractivo.Estado.PUBLICADO).count() == TOTAL_OBJETOS
    usuario = Usuario.objects.get(username="demo")
    assert usuario.check_password("Demo12345!")


def test_seed_demo_es_idempotente():
    call_command("seed_demo")
    call_command("seed_demo")

    assert Escena.objects.count() == TOTAL_ESCENAS
    assert ObjetoInteractivo.objects.count() == TOTAL_OBJETOS
    assert Usuario.objects.filter(username="demo").count() == 1
