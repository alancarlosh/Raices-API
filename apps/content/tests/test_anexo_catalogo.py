"""Pruebas del generador del Anexo B.

Lo que de verdad importa aquí son las tres comprobaciones que deben FALLAR.
La versión anterior de este generador vivía en un temporal y sus guardas se
probaron a mano una vez, lo cual no es lo mismo que quedar probadas: el
script se perdió y con él la única evidencia de que funcionaban. Estas
pruebas alimentan cada guarda con datos roto a propósito.
"""

import pytest

from apps.content.anexo_catalogo import (
    construir,
    empareja_con_semilla,
    normalizar_fuente,
    parsear_bloque1,
)
from apps.content.seed_data import ESCENAS_SEED

VOCAB = """# Vocabulario

## ✅ Bloque 1 — Nuevo, confirmado

### Cocina
| Objeto | Palabra Totonaco | Variante / fuente |
|---|---|---|
| Metate | *xuat'i* | Papantla / Xicotepec |
| Comal | *palhcla* | Los 3 diccionarios |

### Huerto / Milpa (escenario nuevo, exterior)
| Objeto | Palabra Totonaco | Variante / fuente |
|---|---|---|
| Maíz | *cux'i* | Papantla — relevante: capital de la vainilla |
| Limón | *limunax* | — |
| Tijeras | *tijeras* (hispanismo documentado) | Xicotepec |

## ⚠️ Bloque 2 — No encontrado

tlecuil, molinillo
"""

GLOSAS = {"metate", "comal", "maíz", "tijeras"}
ORDEN = ["Cocina", "Huerto"]
ESPERADO = {"Cocina": 2, "Huerto": 2}
TOTAL = 4
EXCLUIDOS = {"limon": "sin fuente anotada"}


def _construir(**cambios):
    kwargs = {
        "orden": ORDEN,
        "esperado_por_escenario": ESPERADO,
        "total_esperado": TOTAL,
        "excluidos": EXCLUIDOS,
    }
    kwargs.update(cambios)
    texto = kwargs.pop("texto", VOCAB)
    glosas = kwargs.pop("glosas", GLOSAS)
    return construir(texto, glosas, **kwargs)


# --- Las tres guardas, alimentadas con datos roto a propósito -------------

def test_falla_si_un_escenario_no_trae_los_terminos_esperados():
    with pytest.raises(ValueError, match="Cocina: 2 términos, se esperaban 3"):
        _construir(esperado_por_escenario={"Cocina": 3, "Huerto": 2}, total_esperado=5)


def test_falla_si_el_total_no_cuadra():
    with pytest.raises(ValueError, match="total 4 términos, se esperaban 73"):
        _construir(total_esperado=73)


def test_falla_si_un_termino_excluido_ya_no_existe_con_ese_nombre():
    """La guarda que más importa: si alguien renombra «Limón» en el archivo, la
    exclusión dejaría de aplicarse en silencio y el total subiría sin que nadie
    lo notara.

    Aquí se le dan conteos consistentes con la fila NO excluida (Huerto 3,
    total 5) para aislar esta guarda; así se comprueba que dispara por sí
    sola y no de rebote.
    """
    with pytest.raises(ValueError, match="se excluyeron 0 filas pero hay 1 declaradas"):
        _construir(
            excluidos={"limonero": "sin fuente anotada"},
            esperado_por_escenario={"Cocina": 2, "Huerto": 3},
            total_esperado=5,
        )


def test_el_conteo_caza_antes_el_renombrado_de_una_exclusion():
    """Defensa en profundidad, y conviene saber el orden: con los conteos
    REALES puestos (los que el anexo afirma), renombrar la exclusión hace
    saltar primero la guarda de conteos, porque la fila de más engorda su
    escenario. La de exclusiones es la segunda red, para el caso en que
    alguien ajuste también los conteos sin darse cuenta de por qué subieron.
    """
    with pytest.raises(ValueError, match="Huerto: 3 términos, se esperaban 2"):
        _construir(excluidos={"limonero": "sin fuente anotada"})


def test_falla_si_un_termino_del_catalogo_no_tiene_fila_en_la_semilla():
    with pytest.raises(ValueError, match="no tienen fila en la semilla: Comal"):
        _construir(glosas={"metate", "maíz", "tijeras"})


# --- El caso feliz y el formato -------------------------------------------

def test_construye_el_anexo_con_el_formato_acordado():
    md = _construir()

    assert md.startswith("# Anexo B — Catálogo de términos")
    assert "4 términos, agrupados por escenario" in md
    assert "| Escenario | Término en español | Traducción al totonaco | Fuente |" in md
    assert "## Cocina (2)" in md
    assert "## Huerto (2)" in md
    # El escenario con título largo se normaliza a su nombre corto.
    assert "Huerto / Milpa" not in md
    assert "**Total: 4 términos.**" in md


def test_marca_hispanismos_y_grafias_con_lh():
    md = _construir()

    assert "| Huerto | Tijeras † |" in md       # hispanismo documentado
    assert "| Cocina | Comal ‡ |" in md          # contiene el dígrafo lh
    assert "| Cocina | Metate |" in md           # sin marcas
    assert "Hispanismos (`†`): 1." in md
    assert "(`‡`): 1." in md


def test_la_entrada_excluida_se_explica_al_final_y_no_en_la_tabla():
    md = _construir()

    assert "| Huerto | Limón" not in md
    assert "Entrada(s) excluida(s) del catálogo por carecer de fuente (1)" in md
    assert "- Limón (*limunax*) — sin fuente anotada." in md


# --- Fuentes y emparejamiento --------------------------------------------

@pytest.mark.parametrize(
    "celda, esperado",
    [
        ("Papantla / Xicotepec", "Aschmann Papantla 1973; Reid y Bishop 1974"),
        ("Los 3 diccionarios", "Aschmann Papantla 1973; Aschmann Sierra 1973; Reid y Bishop 1974"),
        ("Papantla — relevante: capital de la vainilla", "Aschmann Papantla 1973"),
        ("Papantla / Xicotepec / Beck", "Aschmann Papantla 1973; Reid y Bishop 1974; Beck Alto Necaxa"),
        ("—", ""),
    ],
)
def test_normaliza_la_fuente_a_la_forma_corta(celda, esperado):
    assert normalizar_fuente(celda) == esperado


@pytest.mark.parametrize(
    "termino",
    ["Imagen religiosa / santo", "Máquina de coser de pedal", "Telar de cintura"],
)
def test_empareja_las_formas_descriptivas_que_dan_falsos_negativos(termino):
    """Los tres casos que hicieron tropezar a quien cruzó el anexo a mano
    contra los slugs: la semilla guarda "imagen_religiosa" y "maquina_coser"
    en `palabra`, pero la glosa es la etiqueta real en español, y es contra
    ella que hay que comparar."""
    glosas = {glosa for datos in ESCENAS_SEED.values() for _, glosa, _ in datos["objetos"]}

    assert empareja_con_semilla(termino, glosas)


def test_parsea_una_fila_por_objeto_y_les_pone_su_escenario():
    filas = parsear_bloque1(VOCAB)

    assert len(filas) == 5  # 2 de Cocina + 3 de Huerto, incluido el excluido
    assert filas[0] == ("Cocina", "Metate", "*xuat'i*", "Papantla / Xicotepec")
    assert {f[0] for f in filas} == {"Cocina", "Huerto"}
