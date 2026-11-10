"""El viaje completo: respaldar, borrar, restaurar, comparar.

Esto NO prueba que el comando "corre". Prueba lo único que importa de un
respaldo: que los datos vuelven. El 30 de noviembre de 2026 la base de
Render se borra por caducidad del plan gratuito, y ese no es el día para
descubrir que el formato no cargaba.

Se borra DE VERDAD entre medias (no se usa otra base) porque restaurar
sobre datos que ya están no demuestra nada: todo saldría igual aunque el
archivo estuviera vacío.
"""
import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.tests.factories import UsuarioFactory
from apps.content.tests.factories import ObjetoInteractivoFactory
from apps.progress.models import IntentoEscritura, ProgresoUsuario
from apps.telemetria.models import MedicionRendimiento

Usuario = get_user_model()
pytestmark = pytest.mark.django_db


def _poblar():
    """Una muestra de cada cosa que el respaldo tiene que salvar."""
    objeto = ObjetoInteractivoFactory(palabra="comal", glosa_es="comal")
    alumno = UsuarioFactory(username="alumno_respaldo")
    ProgresoUsuario.objects.create(usuario=alumno, objeto=objeto)
    IntentoEscritura.objects.create(
        usuario=alumno, objeto=objeto, texto_ingresado="comal", correcto=True
    )
    MedicionRendimiento.objects.create(
        usuario=alumno, escena="casa", fps_p50=26, fps_p5=14, fps_min=14,
        muestras=40, dpr=0.8, pixeles=234291, mallas=2133,
        gpu="Apple GPU", navegador="Safari", nucleos=4,
        ajustes="sombras=soft;dpr=auto", version="e890c4f",
    )
    return objeto, alumno


def _borrar_datos_de_usuario():
    """Lo que la caducidad de Render se lleva. El catálogo se queda,
    igual que en producción: seed_demo lo vuelve a sembrar al desplegar."""
    MedicionRendimiento.objects.all().delete()
    IntentoEscritura.objects.all().delete()
    ProgresoUsuario.objects.all().delete()
    Usuario.objects.all().delete()


def test_los_datos_vuelven_despues_de_borrarlos(tmp_path):
    objeto, _ = _poblar()
    ruta = tmp_path / "respaldo.json"

    call_command("respaldar", salida=str(ruta), stdout=StringIO())
    _borrar_datos_de_usuario()
    assert Usuario.objects.count() == 0
    assert MedicionRendimiento.objects.count() == 0

    call_command("restaurar", str(ruta), si_de_verdad=True, stdout=StringIO())

    assert Usuario.objects.filter(username="alumno_respaldo").exists()
    assert ProgresoUsuario.objects.count() == 1
    intento = IntentoEscritura.objects.get()
    assert intento.texto_ingresado == "comal" and intento.correcto is True
    medida = MedicionRendimiento.objects.get()
    # Las cifras EXACTAS, no solo que exista la fila: son la evidencia del
    # capítulo de resultados y un respaldo que redondea no sirve.
    assert (medida.fps_p50, medida.fps_p5, medida.fps_min) == (26, 14, 14)
    assert medida.ajustes == "sombras=soft;dpr=auto"
    assert medida.version == "e890c4f"
    assert medida.escena == "casa"
    assert medida.usuario.username == "alumno_respaldo"
    assert ProgresoUsuario.objects.get().objeto_id == objeto.id


def test_el_respaldo_no_lleva_el_catalogo(tmp_path):
    """Si lo llevara, restaurar pisaría lo que seed_demo acaba de sembrar
    y devolvería una versión vieja del temario sin que nadie lo note."""
    _poblar()
    ruta = tmp_path / "respaldo.json"
    call_command("respaldar", salida=str(ruta), stdout=StringIO())

    modelos = {fila["model"] for fila in json.loads(ruta.read_text())}
    assert "content.objetointeractivo" not in modelos
    assert "content.escena" not in modelos
    assert "languages.lengua" not in modelos


def test_sin_cuentas_no_escribe_datos_personales(tmp_path):
    _poblar()
    ruta = tmp_path / "anonimo.json"
    call_command("respaldar", salida=str(ruta), sin_cuentas=True, stdout=StringIO())

    crudo = ruta.read_text()
    modelos = {fila["model"] for fila in json.loads(crudo)}
    assert not any(m.startswith("auth.") or m.startswith("accounts.") for m in modelos)
    # Y la telemetría, que es para lo que sirve ese modo, sí está.
    assert "telemetria.medicionrendimiento" in modelos


def test_restaurar_exige_confirmacion(tmp_path):
    _poblar()
    ruta = tmp_path / "respaldo.json"
    call_command("respaldar", salida=str(ruta), stdout=StringIO())
    with pytest.raises(CommandError, match="si-de-verdad"):
        call_command("restaurar", str(ruta), stdout=StringIO())


def test_restaurar_se_niega_si_falta_el_catalogo(tmp_path):
    """El caso que dejaría la base a medias: el respaldo referencia
    objetos por id y la base destino no los tiene sembrados."""
    objeto, _ = _poblar()
    ruta = tmp_path / "respaldo.json"
    call_command("respaldar", salida=str(ruta), stdout=StringIO())
    _borrar_datos_de_usuario()
    objeto.delete()

    with pytest.raises(CommandError, match="catálogo"):
        call_command("restaurar", str(ruta), si_de_verdad=True, stdout=StringIO())
    # Y que NO haya escrito nada a medias.
    assert Usuario.objects.count() == 0


def test_respaldar_avisa_si_no_hay_nada(tmp_path):
    """Contra la base de producción, un respaldo vacío es una alarma."""
    with pytest.raises(CommandError, match="NADA"):
        call_command("respaldar", salida=str(tmp_path / "x.json"), stdout=StringIO())
