import pytest
from django.core.management import call_command

from apps.accounts.models import Usuario
from apps.accounts.tests.factories import UsuarioFactory
from apps.content.models import Escena, ObjetoInteractivo
from apps.content.seed_data import ESCENAS_SEED
from apps.progress.models import IntentoEscritura, ProgresoUsuario

TOTAL_ESCENAS = len(ESCENAS_SEED)
TOTAL_OBJETOS = sum(len(datos["objetos"]) for datos in ESCENAS_SEED.values())

pytestmark = pytest.mark.django_db


def _objeto_fuera_del_seed_con_progreso(usuario):
    """Simula una palabra que estuvo en el temario, un usuario la practicó, y
    después salió de ESCENAS_SEED (como las 5 piezas del Baño en octubre)."""
    call_command("seed_demo")
    escena = Escena.objects.get(codigo="bano")
    objeto = ObjetoInteractivo.objects.create(
        escena=escena,
        lengua=escena.lengua,
        palabra="inodoro",
        glosa_es="inodoro",
        sprite_key="toilet_a",
        audio_ogg="https://cdn.example.com/a.ogg",
        audio_m4a="https://cdn.example.com/a.m4a",
        x=0,
        y=0,
        width=64,
        height=64,
        estado=ObjetoInteractivo.Estado.PUBLICADO,
    )
    ProgresoUsuario.objects.create(usuario=usuario, objeto=objeto)
    IntentoEscritura.objects.create(
        usuario=usuario, objeto=objeto, texto_ingresado="inodoro", correcto=True
    )
    return objeto


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


def test_seed_demo_retira_sin_borrar_y_conserva_el_progreso():
    usuario = UsuarioFactory()
    objeto = _objeto_fuera_del_seed_con_progreso(usuario)

    call_command("seed_demo")

    objeto.refresh_from_db()
    assert objeto.estado == ObjetoInteractivo.Estado.RETIRADO
    # Lo que de verdad importa: el progreso del usuario sigue ahí.
    assert ProgresoUsuario.objects.filter(objeto=objeto, usuario=usuario).exists()
    assert IntentoEscritura.objects.filter(objeto=objeto, usuario=usuario).exists()


def test_objeto_retirado_desaparece_del_recorrido_y_de_los_porcentajes():
    from apps.content.selectors import escena_get_publicada
    from apps.progress.selectors import progreso_resumen

    usuario = UsuarioFactory()
    objeto = _objeto_fuera_del_seed_con_progreso(usuario)
    escena_id = objeto.escena_id

    antes = next(e for e in progreso_resumen(usuario=usuario) if e["escena_id"] == escena_id)
    call_command("seed_demo")
    despues = next(e for e in progreso_resumen(usuario=usuario) if e["escena_id"] == escena_id)

    escena = escena_get_publicada(escena_id=escena_id)
    assert objeto.id not in [o.id for o in escena.objetos.all()]
    # Ya retirado, no infla ni el total ni lo descubierto de la escena.
    assert despues["total_objetos"] == antes["total_objetos"] - 1
    assert despues["objetos_descubiertos"] == antes["objetos_descubiertos"] - 1


def test_palabra_que_vuelve_al_seed_se_republica_con_su_progreso_historico():
    usuario = UsuarioFactory()
    objeto = _objeto_fuera_del_seed_con_progreso(usuario)
    call_command("seed_demo")
    objeto.refresh_from_db()
    assert objeto.estado == ObjetoInteractivo.Estado.RETIRADO

    # Vuelve al temario: el update_or_create del comando la repone sola.
    bano = ESCENAS_SEED["bano"]["objetos"]
    ESCENAS_SEED["bano"]["objetos"] = bano + [("inodoro", "inodoro", "toilet_a")]
    try:
        call_command("seed_demo")
    finally:
        ESCENAS_SEED["bano"]["objetos"] = bano

    objeto.refresh_from_db()
    assert objeto.estado == ObjetoInteractivo.Estado.PUBLICADO
    assert ProgresoUsuario.objects.filter(objeto=objeto, usuario=usuario).exists()


def test_seed_demo_purgar_si_borra_y_lo_advierte():
    usuario = UsuarioFactory()
    objeto = _objeto_fuera_del_seed_con_progreso(usuario)

    call_command("seed_demo", "--purgar")

    assert not ObjetoInteractivo.objects.filter(id=objeto.id).exists()
    # Y por cascada se fue el progreso -- de ahí que no sea el comportamiento
    # por defecto y que el comando lo diga en voz alta antes de hacerlo.
    assert not ProgresoUsuario.objects.filter(objeto_id=objeto.id).exists()
    assert not IntentoEscritura.objects.filter(objeto_id=objeto.id).exists()
