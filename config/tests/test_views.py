import pytest
from rest_framework.test import APIClient


def test_salud_responde_200_sin_sesion():
    """Es el unico endpoint que un visitante sin sesion puede llamar antes
    de escribir ninguna credencial -- si alguna vez quedara detras de
    IsAuthenticated (el default del proyecto, ver REST_FRAMEWORK en
    settings.py) dejaria de servir para lo que existe: despertar el
    servicio ANTES de que haya nada que autenticar."""
    respuesta = APIClient().get("/api/salud/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}


@pytest.mark.django_db
def test_salud_no_hace_ninguna_consulta_a_la_base(django_assert_num_queries):
    """El punto entero es no despertar mas de lo necesario: si esto
    empezara a tocar la base de datos, dejaria de ser el ping barato que
    se puede llamar en cada carga de pantalla sin pensarlo.

    `django_db` esta puesto para que `django_assert_num_queries` pueda
    contar de verdad, no para que la vista necesite base de datos -- sin
    la marca, pytest-django BLOQUEA cualquier acceso y la prueba fallaria
    por el motivo equivocado (acceso prohibido) en vez del que importa
    (cero consultas)."""
    with django_assert_num_queries(0):
        APIClient().get("/api/salud/")
