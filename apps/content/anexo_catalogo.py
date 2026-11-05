"""Construye el Anexo B de la tesis: el catálogo de términos con traducción
al totonaco documentada.

POR QUÉ ESTO ES UN MÓDULO Y NO UN SCRIPT SUELTO. La primera versión vivía en
un directorio temporal y se perdió al limpiarse. El anexo sobrevivió, pero
lo que lo VALIDABA no, y eso lo dejaba en la misma situación que el resto de
las cifras de este proyecto: un archivo sin forma de volver a derivarse. El
catálogo ya pasó de 109 a 74 y de 74 a 73, y cada corrección salió de volver
a derivar, no de recordar.

QUÉ VALIDA, y por qué cada comprobación existe:

1. Los conteos por escenario y el total. Si el archivo de vocabulario crece o
   mengua, el anexo dejaría de cuadrar con la cifra que el cuerpo de la tesis
   afirma; es preferible que la generación falle a emitir un anexo que
   contradiga al Capítulo 3.
2. Que cada término excluido siga existiendo con ese nombre en el archivo.
   Es la más importante: si alguien renombra «Limón», la exclusión dejaría de
   aplicarse EN SILENCIO y el anexo volvería a 74 sin que nadie lo notara.
3. Que cada término del catálogo siga teniendo fila en la semilla. Un anexo
   con filas que la aplicación no tiene es justo lo que un sinodal podría
   comprobar abriendo el sistema.

Las tres levantan ValueError. El comando las convierte en CommandError, y
apps/content/tests/test_anexo_catalogo.py comprueba que fallan DE VERDAD
alimentándolas con datos roto a propósito — la versión anterior se verificó
a mano una vez, que no es lo mismo que quedar verificada.
"""

import re
import unicodedata

# --- El catálogo real, declarado ------------------------------------------

ORDEN_ESCENARIOS = ["Cocina", "Sala", "Recámara", "Baño", "Estudio", "Patio", "Corral", "Huerto"]

# El Bloque 1 del archivo trae 74 filas; el catálogo son 73 (ver EXCLUIDOS).
ESPERADO_POR_ESCENARIO = {
    "Cocina": 12, "Sala": 7, "Recámara": 6, "Baño": 9,
    "Estudio": 8, "Patio": 9, "Corral": 10, "Huerto": 12,
}
TOTAL_ESPERADO = 73

# Términos del Bloque 1 que NO entran al catálogo, con el motivo escrito.
# El Capítulo 3 declara el criterio ("integran el catálogo únicamente aquellos
# cuya traducción está respaldada por una fuente"), así que una entrada sin
# fuente anotada haría falsa esa frase. El objeto sigue en el escenario; lo
# que no es, mientras no tenga respaldo, es entrada de catálogo. Si algún día
# aparece en alguna de las fuentes, se quita de aquí y el total sube solo.
EXCLUIDOS = {
    "limon": "sin fuente anotada en el archivo de vocabulario (columna «—»)",
}

# Los cuatro que el propio archivo nombra en "Próximos pasos".
HISPANISMOS = {"palangana", "estropajo", "tijeras", "tambor"}

# El archivo advierte que el OCR de los 3 diccionarios confunde el dígrafo
# ⟨lh⟩ con "lj", "ll", "Ij" o "IT". Estas grafías son las que requieren
# cotejo contra el escaneo original antes de darse por definitivas.
OCR_LH = re.compile(r"lh|Lh|LH|lj|Ij|IJ|ll|IT|lT")

# Forma corta y consistente: las fichas completas van en la bibliografía, y
# repetirlas en 73 filas sería ilegible.
FUENTE_CORTA = {
    "papantla": "Aschmann Papantla 1973",
    "sierra": "Aschmann Sierra 1973",
    "xicotepec": "Reid y Bishop 1974",
    "beck": "Beck Alto Necaxa",
}
LOS_TRES = ["Aschmann Papantla 1973", "Aschmann Sierra 1973", "Reid y Bishop 1974"]

# El archivo titula algunos escenarios con nombre largo.
ALIAS_ESCENARIO = {
    "Patio / Traspatio (escenario nuevo, exterior)": "Patio",
    "Corral / Gallinero (escenario nuevo, exterior)": "Corral",
    "Huerto / Milpa (escenario nuevo, exterior)": "Huerto",
}


# --- Utilidades -----------------------------------------------------------

def sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    limpio = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", limpio).strip()


def clave_termino(termino: str) -> str:
    """La parte del término que lo identifica, sin la glosa descriptiva.

    El archivo usa formas descriptivas ("Horno de leña", "Imagen religiosa /
    santo", "Metlapil (mano de metate)") y hay que poder emparejarlas con la
    semilla, que usa la etiqueta corta.
    """
    return sin_acentos(termino.split("(")[0].split("/")[0])


def normalizar_fuente(celda: str) -> str:
    """'Papantla / Xicotepec' -> 'Aschmann Papantla 1973; Reid y Bishop 1974'."""
    celda = re.split(r"\s+—\s+", celda)[0].strip()  # corta comentarios tras guion largo
    if not celda or celda == "—":
        return ""
    if "3 diccionarios" in celda:
        return "; ".join(LOS_TRES)
    salida = []
    for parte in celda.split("/"):
        corta = FUENTE_CORTA.get(parte.strip().lower())
        valor = corta or parte.strip()
        if valor and valor not in salida:
            salida.append(valor)
    return "; ".join(salida)


def parsear_bloque1(texto: str) -> list[tuple[str, str, str, str]]:
    """(escenario, término, totonaco, fuente cruda) por cada fila del Bloque 1."""
    cuerpo = texto.split("## ✅ Bloque 1")[1].split("## ⚠️ Bloque 2")[0]
    filas, escenario = [], None
    for linea in cuerpo.splitlines():
        if linea.startswith("### "):
            titulo = linea[4:].strip()
            escenario = ALIAS_ESCENARIO.get(titulo, titulo)
        elif linea.startswith("|") and "---" not in linea and "Palabra Totonaco" not in linea:
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if len(celdas) >= 3 and celdas[0]:
                filas.append((escenario, celdas[0], celdas[1], celdas[2]))
    return filas


def empareja_con_semilla(termino: str, glosas: set[str]) -> bool:
    """¿Este término del anexo tiene fila en la semilla?

    Se compara contra las GLOSAS (`glosa_es`, la etiqueta en español real) y
    no contra los slugs de `palabra`: el slug va sin acentos y con guion bajo
    ("imagen_religiosa", "maquina_coser"), así que compararlo contra la forma
    descriptiva del anexo da falsos negativos. Esto le costó dos intentos a
    quien lo comprobó a mano, con estos tres: "Imagen religiosa / santo",
    "Máquina de coser de pedal" y "Telar de cintura". Queda resuelto aquí
    para que nadie vuelva a tropezar con ello.
    """
    base = clave_termino(termino)
    normalizadas = {sin_acentos(g) for g in glosas}
    if base in normalizadas:
        return True
    # La semilla puede usar una etiqueta más corta que la forma descriptiva
    # del anexo ("horno" vs "Horno de leña"), o al revés.
    return any(base.startswith(g + " ") or g.startswith(base + " ") for g in normalizadas)


# --- Construcción --------------------------------------------------------

def construir(
    texto_vocabulario: str,
    glosas_semilla: set[str],
    *,
    orden: list[str] | None = None,
    esperado_por_escenario: dict[str, int] | None = None,
    total_esperado: int | None = None,
    excluidos: dict[str, str] | None = None,
) -> str:
    """Devuelve el Markdown del anexo, o levanta ValueError si algo no cuadra.

    Los parámetros con nombre existen para poder probar las comprobaciones
    con datos sintéticos; el comando usa los valores reales de este módulo.
    """
    orden = orden if orden is not None else ORDEN_ESCENARIOS
    esperado_por_escenario = (
        esperado_por_escenario if esperado_por_escenario is not None else ESPERADO_POR_ESCENARIO
    )
    total_esperado = total_esperado if total_esperado is not None else TOTAL_ESPERADO
    excluidos = excluidos if excluidos is not None else EXCLUIDOS

    por_escenario: dict[str, list] = {e: [] for e in orden}
    excluidos_vistos: list[tuple[str, str, str]] = []
    sin_fila_en_semilla: list[str] = []

    for escenario, termino, totonaco, fuente_cruda in parsear_bloque1(texto_vocabulario):
        clave = clave_termino(termino)
        if clave in excluidos:
            excluidos_vistos.append((termino, totonaco, excluidos[clave]))
            continue
        if escenario not in por_escenario:
            raise ValueError(f"escenario inesperado en el archivo de vocabulario: {escenario!r}")
        if not empareja_con_semilla(termino, glosas_semilla):
            sin_fila_en_semilla.append(termino)
        por_escenario[escenario].append(
            (
                termino,
                totonaco,
                normalizar_fuente(fuente_cruda),
                clave in HISPANISMOS or "hispanismo" in totonaco.lower(),
                bool(OCR_LH.search(totonaco)),
            )
        )

    # (1) conteos por escenario y total
    for escenario in orden:
        real, esperado = len(por_escenario[escenario]), esperado_por_escenario[escenario]
        if real != esperado:
            raise ValueError(f"{escenario}: {real} términos, se esperaban {esperado}")
    total = sum(len(v) for v in por_escenario.values())
    if total != total_esperado:
        raise ValueError(f"total {total} términos, se esperaban {total_esperado}")

    # (2) cada exclusión declarada tiene que seguir existiendo con ese nombre
    if len(excluidos_vistos) != len(excluidos):
        raise ValueError(
            f"se excluyeron {len(excluidos_vistos)} filas pero hay {len(excluidos)} declaradas "
            "-- probablemente cambió el nombre del término en el archivo de vocabulario, "
            "y la exclusión dejaría de aplicarse sin que nada lo avisara"
        )

    # (3) ningún término del catálogo puede faltar en la semilla
    if sin_fila_en_semilla:
        raise ValueError(
            "términos del catálogo que no tienen fila en la semilla: "
            + ", ".join(sin_fila_en_semilla)
        )

    return _render(por_escenario, orden, total, excluidos_vistos)


def _render(por_escenario, orden, total, excluidos_vistos) -> str:
    """El formato de salida, que NO debe cambiar sin avisar: ya está
    convertido a LaTeX en la tesis."""
    out = [
        "# Anexo B — Catálogo de términos con traducción al totonaco documentada\n",
        "Generado por máquina desde `Vocabulario_Totonaco_Casa_Rural.md` (Bloque 1) y "
        "cotejado contra la semilla de contenido de Raíces-API "
        f"(`apps/content/seed_data.py`). {total} términos, agrupados por escenario.\n",
        "**Marcas:** `†` hispanismo documentado en la propia fuente (no voz nativa "
        "distinta). `‡` la grafía contiene el dígrafo ⟨lh⟩ o una de sus confusiones "
        "de OCR (lj / ll / Ij / IT): requiere cotejo contra el escaneo original.\n",
        "**Fuentes** (fichas completas en la bibliografía): Aschmann Papantla 1973 · "
        "Aschmann Sierra 1973 · Reid y Bishop 1974 · Beck Alto Necaxa.\n",
    ]

    n_hisp = n_lh = 0
    for escenario in orden:
        out.append(f"\n## {escenario} ({len(por_escenario[escenario])})\n")
        out.append("| Escenario | Término en español | Traducción al totonaco | Fuente |")
        out.append("|---|---|---|---|")
        for termino, totonaco, fuente, hisp, lh in por_escenario[escenario]:
            marcas = ("†" if hisp else "") + ("‡" if lh else "")
            n_hisp += bool(hisp)
            n_lh += bool(lh)
            etiqueta = f"{termino} {marcas}".strip()
            out.append(
                f"| {escenario} | {etiqueta} | {totonaco} | "
                f"{fuente or '**(sin fuente anotada)**'} |"
            )

    out.append("\n---\n")
    out.append(f"**Total: {total} términos.** Hispanismos (`†`): {n_hisp}. ")
    out.append(f"Grafías con ⟨lh⟩ o su confusión de OCR (`‡`): {n_lh}.\n")

    if excluidos_vistos:
        out.append(
            f"\n**Entrada(s) excluida(s) del catálogo por carecer de fuente "
            f"({len(excluidos_vistos)}):**\n"
        )
        for termino, totonaco, motivo in excluidos_vistos:
            out.append(f"- {termino} ({totonaco}) — {motivo}.")
        out.append(
            "\nEl criterio de inclusión del catálogo es que la traducción esté "
            "respaldada por una fuente; esta(s) no lo está(n), de modo que no figura(n) "
            "aquí. El objeto correspondiente sigue presente en el escenario: lo que no "
            "constituye es una entrada de catálogo. Si la traducción aparece más "
            "adelante en alguna de las fuentes consultadas, la entrada se incorpora y "
            "el total asciende.\n"
        )

    out.append(
        f"\nLos {total} términos tienen fila correspondiente en la semilla del sistema "
        "(verificado por máquina): el anexo no contiene filas que la aplicación no "
        "tenga.\n"
    )
    return "\n".join(out)
