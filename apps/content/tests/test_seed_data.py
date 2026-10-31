"""Tripwire para los conteos de la semilla.

No prueba comportamiento: prueba que las cifras que este proyecto CITA sigan
siendo las que los datos dicen. Existe por un caso real — el encabezado de
seed_data.py afirmaba "108 objetos" cuando había 102 filas (el 108 era el
número de etiquetas del recorrido 3D, de otro repo), nadie volvió a
derivarlo en semanas, y acabó citado como tamaño del catálogo de vocabulario
en el Capítulo 3 de la tesis, que llegó a afirmar 109 términos.

La idea no es que estos números sean sagrados: es que al cambiar el
vocabulario esta prueba FALLE, para que la cifra se actualice a conciencia
—y con ella el anexo de la tesis, que se genera de estos datos— en vez de
quedar una vieja envejeciendo en un comentario.
"""

from apps.content.seed_data import ESCENAS_SEED, conteos, glosa_de, palabras_unicas

# Sin fecha a propósito: esto no registra una medición pasada, es la
# expectativa PRESENTE, y la prueba de abajo garantiza que no pueda quedarse
# vieja en silencio. Una cifra que describe el estado presente se deriva o se
# fija con tripwire; la fecha es para las que registran una medición con sus
# condiciones (ver la cifra de sprites en seed_data.py, que no se puede
# derivar desde este repo).
#
# Si cambian los datos, actualiza AQUI y revisa también el Anexo B de la
# tesis (~/Documents/Anexo_B_Catalogo_Totonaco.md), que se genera cruzando
# esta semilla con el archivo de vocabulario. Y no confundas estas cifras
# con el tamaño del catálogo: `filas` y `palabras_unicas` son del sistema,
# el catálogo son los términos con fuente documentada, que son menos.
# 2026-10-30: bajan de 102/95/98 al salir "computadora" del temario (ver la
# nota en seed_data.py). Actualizado a conciencia porque el tripwire falló,
# que es para lo que está. De paso cazó los dos audios de fixture que se
# quedaban huérfanos (ver test_load_placeholder_audio_fixtures).
CONTEOS_DOCUMENTADOS = {
    "escenas": 8,
    "filas": 101,
    "palabras_unicas": 94,
    "sprite_keys_unicas": 97,
}


def test_los_conteos_citados_siguen_siendo_los_reales():
    assert conteos() == CONTEOS_DOCUMENTADOS


def test_filas_y_palabras_unicas_no_son_lo_mismo():
    """Las 7 repeticiones entre cuartos son la diferencia entre "cuántas filas
    tiene la base" y "cuántos términos de vocabulario hay" — la confusión que
    infló el conteo del catálogo."""
    c = conteos()
    assert c["filas"] - c["palabras_unicas"] == 7


def test_cada_slug_tiene_una_sola_glosa():
    """Un slug con dos glosas distintas rompería dos cosas a la vez: el audio
    (un archivo por slug, pero ¿cuál se pronuncia?) y el emparejamiento del
    frontend, que busca por glosa."""
    glosas_por_slug = {}
    for datos in ESCENAS_SEED.values():
        for slug, glosa, _ in datos["objetos"]:
            glosas_por_slug.setdefault(slug, set()).add(glosa)
    ambiguos = {s: g for s, g in glosas_por_slug.items() if len(g) > 1}
    assert not ambiguos, f"slugs con más de una glosa: {ambiguos}"


def test_glosa_de_resuelve_todos_los_slugs():
    """`glosa_de` cae al propio slug cuando no encuentra la palabra, así que un
    fallo aquí haría que el TTS pronuncie el slug sin que nada avise."""
    sin_glosa = [p for p in palabras_unicas() if glosa_de(p) == p and "_" in p]
    assert not sin_glosa, f"slugs que el TTS pronunciaría crudos: {sin_glosa}"
