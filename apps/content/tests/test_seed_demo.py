import pytest
from django.core.management import call_command

from apps.accounts.models import Usuario
from apps.accounts.tests.factories import UsuarioFactory
from apps.content.models import Escena, ObjetoInteractivo
from apps.content.seed_data import ESCENAS_SEED
from apps.progress.models import IntentoEscritura, ProgresoUsuario
from apps.progress.selectors import progreso_resumen, progreso_total

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


def test_sin_la_bandera_no_siembra_ningun_progreso():
    """Opt-in de verdad: el seed normal --el que corre en cada build de
    Render-- no debe inventar uso."""
    call_command("seed_demo")

    assert not ProgresoUsuario.objects.exists()
    assert not IntentoEscritura.objects.exists()


def test_con_progreso_siembra_una_muestra_reconocible():
    call_command("seed_demo", "--con-progreso")
    demo = Usuario.objects.get(username="demo")

    resumen = progreso_resumen(usuario=demo)
    con_progreso = [e for e in resumen if e["objetos_descubiertos"]]

    # Pocas escenas tocadas, de las ocho: se reconoce como muestra.
    assert len(con_progreso) == 3
    assert len(resumen) == 8
    for escena in resumen:
        # Ninguna escena al 100%: un 100% parecería una sesión completa.
        assert escena["porcentaje"] < 100
        # Descubiertos >= dominados siempre, nunca al revés.
        assert escena["objetos_descubiertos"] >= escena["objetos_dominados"]

    total = progreso_total(resumen_por_escena=resumen)
    assert total["objetos_descubiertos"] == 9
    assert total["objetos_dominados"] == 4
    # Y no es todo el catálogo, ni de lejos.
    assert total["porcentaje"] < 15


def test_con_progreso_deja_un_objeto_descubierto_con_el_ultimo_intento_fallido():
    """Para que la pantalla muestre por qué 'descubierto' y 'dominado' son
    métricas distintas, y no dos números que casi coinciden."""
    call_command("seed_demo", "--con-progreso")
    demo = Usuario.objects.get(username="demo")

    fallidos = IntentoEscritura.objects.filter(usuario=demo, correcto=False)

    assert fallidos.count() == 1
    objeto = fallidos.first().objeto
    assert ProgresoUsuario.objects.filter(usuario=demo, objeto=objeto).exists()


def test_los_intentos_sembrados_son_coherentes_no_decretados():
    """Un intento marcado correcto tiene que serlo porque el texto coincide
    con la palabra; si se creara la fila a mano podría decir `correcto=True`
    sobre un texto que no coincide, y eso no se sostiene."""
    call_command("seed_demo", "--con-progreso")
    demo = Usuario.objects.get(username="demo")

    for intento in IntentoEscritura.objects.filter(usuario=demo):
        assert intento.correcto == (intento.texto_ingresado == intento.objeto.palabra)


def test_con_progreso_es_idempotente():
    call_command("seed_demo", "--con-progreso")
    call_command("seed_demo", "--con-progreso")
    demo = Usuario.objects.get(username="demo")

    assert ProgresoUsuario.objects.filter(usuario=demo).count() == 9
    assert IntentoEscritura.objects.filter(usuario=demo).count() == 5


def test_el_progreso_sembrado_solo_toca_la_cuenta_demo():
    otro = UsuarioFactory(username="alguien_mas")

    call_command("seed_demo", "--con-progreso")

    assert not ProgresoUsuario.objects.filter(usuario=otro).exists()
    assert not IntentoEscritura.objects.filter(usuario=otro).exists()


def test_seed_demo_purgar_si_borra_y_lo_advierte():
    usuario = UsuarioFactory()
    objeto = _objeto_fuera_del_seed_con_progreso(usuario)

    call_command("seed_demo", "--purgar")

    assert not ObjetoInteractivo.objects.filter(id=objeto.id).exists()
    # Y por cascada se fue el progreso -- de ahí que no sea el comportamiento
    # por defecto y que el comando lo diga en voz alta antes de hacerlo.
    assert not ProgresoUsuario.objects.filter(objeto_id=objeto.id).exists()
    assert not IntentoEscritura.objects.filter(objeto_id=objeto.id).exists()
