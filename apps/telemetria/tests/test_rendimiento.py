"""Pruebas del endpoint de telemetría de rendimiento.

Lo que se prueba aquí NO es "el modelo guarda campos" — eso lo garantiza
Django. Se prueba lo que puede arruinar el capítulo de resultados de la
tesis: que una fila incoherente no entre, que nadie escriba mediciones a
nombre de otro, y que el resumen ponga lo PEOR arriba.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.telemetria.models import MedicionRendimiento

Usuario = get_user_model()


def medida(**cambios):
    base = {
        "escena": "casa", "fps_p50": 42, "fps_p5": 31, "fps_min": 28,
        "muestras": 40, "dpr": 1.25, "pixeles": 1_908_750, "mallas": 2060,
        "gpu": "Apple M1", "navegador": "Brave/1.7", "nucleos": 8,
    }
    base.update(cambios)
    return base


@pytest.fixture
def alumno(db):
    return Usuario.objects.create_user(username="alumno1", password="x" * 12)


@pytest.fixture
def cliente(alumno):
    c = APIClient()
    c.force_authenticate(user=alumno)
    return c


def test_guarda_una_medicion(cliente, alumno):
    r = cliente.post(reverse("rendimiento-crear"), medida(), format="json")
    assert r.status_code == 201, r.data
    m = MedicionRendimiento.objects.get()
    assert m.usuario == alumno
    assert m.fps_p5 == 31


def test_sin_sesion_no_entra(db):
    r = APIClient().post(reverse("rendimiento-crear"), medida(), format="json")
    assert r.status_code in (401, 403)
    assert MedicionRendimiento.objects.count() == 0


def test_el_usuario_no_se_puede_falsificar(cliente, alumno, db):
    """El cuerpo trae `usuario`; tiene que ignorarse y mandar el del token."""
    otro = Usuario.objects.create_user(username="otro", password="y" * 12)
    r = cliente.post(reverse("rendimiento-crear"),
                     medida(usuario=otro.pk), format="json")
    assert r.status_code == 201, r.data
    assert MedicionRendimiento.objects.get().usuario == alumno


@pytest.mark.parametrize("cambio, porque", [
    ({"muestras": 5}, "pocos segundos: el p5 no significa nada"),
    ({"fps_p50": 10, "fps_p5": 30, "fps_min": 28}, "p5 por encima de p50"),
    ({"fps_p50": 42, "fps_p5": 31, "fps_min": 35}, "mínimo por encima del p5"),
    ({"fps_p50": 900}, "cuadros/s imposibles"),
    ({"dpr": 0.0}, "dpr fuera de rango"),
    ({"pixeles": 999_000_000}, "píxeles imposibles"),
])
def test_rechaza_filas_incoherentes(cliente, cambio, porque):
    r = cliente.post(reverse("rendimiento-crear"), medida(**cambio), format="json")
    assert r.status_code == 400, f"debería rechazarse ({porque}): {r.data}"
    assert MedicionRendimiento.objects.count() == 0


def test_la_gpu_puede_faltar(cliente):
    """Firefox y los navegadores con anti-huella no exponen la GPU. Que
    falte es un dato, no un error: la fila tiene que entrar igual."""
    r = cliente.post(reverse("rendimiento-crear"),
                     medida(gpu="", nucleos=None, memoria_gb=None), format="json")
    assert r.status_code == 201, r.data


def test_resumen_es_solo_para_personal(cliente):
    assert cliente.get(reverse("rendimiento-resumen")).status_code == 403


def test_resumen_pone_lo_peor_arriba(db):
    jefe = Usuario.objects.create_superuser(username="jefe", password="z" * 12)
    buena = Usuario.objects.create_user(username="buena", password="z" * 12)
    mala = Usuario.objects.create_user(username="mala", password="z" * 12)
    MedicionRendimiento.objects.create(
        usuario=buena, escena="casa", fps_p50=60, fps_p5=55, fps_min=50,
        muestras=40, dpr=1.25, pixeles=1_000_000, mallas=2000, gpu="rapida")
    MedicionRendimiento.objects.create(
        usuario=mala, escena="casa", fps_p50=20, fps_p5=12, fps_min=9,
        muestras=40, dpr=0.8, pixeles=1_000_000, mallas=2000, gpu="lenta")

    c = APIClient()
    c.force_authenticate(user=jefe)
    r = c.get(reverse("rendimiento-resumen"))
    assert r.status_code == 200
    filas = r.data["filas"]
    assert r.data["total"] == 2
    assert filas[0]["gpu"] == "lenta", "la tabla tiene que abrir por lo que sufre"
    assert filas[0]["p5_medio"] == 12.0
    assert filas[0]["peor"] == 9


def test_guarda_con_que_ajustes_y_version_se_midio(cliente):
    """Lo que separa un "antes" de un "después".

    Sin estos dos campos, dos filas tomadas a propósito con ajustes
    distintos llegan al admin idénticas y compararlas es inventar.
    """
    r = cliente.post(
        reverse("rendimiento-crear"),
        medida(ajustes="sombras=no;dpr=fijo", version="e890c4f"),
        format="json",
    )
    assert r.status_code == 201, r.data
    m = MedicionRendimiento.objects.get()
    assert m.ajustes == "sombras=no;dpr=fijo"
    assert m.version == "e890c4f"


def test_una_fila_sin_ajustes_ni_version_sigue_entrando(cliente):
    """COMPATIBILIDAD, y no es teórica.

    Cuando esto se despliegue habrá alumnos con el bundle ANTERIOR ya
    cargado en el teléfono, que manda la fila sin estos campos. Si el
    serializador los exigiera, esas medidas se perderían en silencio
    (el cliente no reintenta) y justo son las del "antes" que queremos
    comparar.
    """
    datos = medida()
    assert "ajustes" not in datos and "version" not in datos
    r = cliente.post(reverse("rendimiento-crear"), datos, format="json")
    assert r.status_code == 201, r.data
    m = MedicionRendimiento.objects.get()
    assert m.ajustes == "" and m.version == ""
