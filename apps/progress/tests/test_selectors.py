import pytest

from apps.accounts.tests.factories import UsuarioFactory
from apps.content.tests.factories import EscenaFactory, ObjetoInteractivoFactory
from apps.progress import selectors, services

pytestmark = pytest.mark.django_db


def test_objeto_dominado_si_el_intento_mas_reciente_es_correcto():
    escena = EscenaFactory()
    objeto = ObjetoInteractivoFactory(escena=escena, palabra="silla")
    usuario = UsuarioFactory()

    services.intento_escritura_registrar(usuario=usuario, objeto_id=objeto.id, texto_ingresado="incorrecta")
    services.intento_escritura_registrar(usuario=usuario, objeto_id=objeto.id, texto_ingresado="silla")

    resumen = selectors.progreso_resumen(usuario=usuario)
    assert resumen[0]["objetos_dominados"] == 1
    assert resumen[0]["porcentaje_dominado"] == 100.0


def test_objeto_no_dominado_si_el_intento_mas_reciente_es_incorrecto():
    """Acertar una vez y luego fallar NO debe seguir contando como dominado —
    el dominio se deriva del estado más reciente, no de un logro permanente."""
    escena = EscenaFactory()
    objeto = ObjetoInteractivoFactory(escena=escena, palabra="silla")
    usuario = UsuarioFactory()

    services.intento_escritura_registrar(usuario=usuario, objeto_id=objeto.id, texto_ingresado="silla")
    services.intento_escritura_registrar(usuario=usuario, objeto_id=objeto.id, texto_ingresado="incorrecta")

    resumen = selectors.progreso_resumen(usuario=usuario)
    assert resumen[0]["objetos_dominados"] == 0
    assert resumen[0]["porcentaje_dominado"] == 0.0


def test_progreso_total_agrega_por_escena():
    escena1 = EscenaFactory()
    escena2 = EscenaFactory()
    objeto1 = ObjetoInteractivoFactory(escena=escena1, palabra="silla")
    ObjetoInteractivoFactory(escena=escena1, palabra="mesa")
    objeto2 = ObjetoInteractivoFactory(escena=escena2, palabra="cama")
    usuario = UsuarioFactory()

    services.progreso_marcar_descubierto(usuario=usuario, objeto_id=objeto1.id)
    services.intento_escritura_registrar(usuario=usuario, objeto_id=objeto2.id, texto_ingresado="cama")

    por_escena = selectors.progreso_resumen(usuario=usuario)
    total = selectors.progreso_total(resumen_por_escena=por_escena)

    assert total["total_objetos"] == 3
    assert total["objetos_descubiertos"] == 1
    assert total["objetos_dominados"] == 1
