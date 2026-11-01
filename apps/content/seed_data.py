"""Datos de fixture compartidos entre `seed_demo` y `generate_placeholder_audio`.

ADVERTENCIA: el totonaco YA ES la lengua real confirmada del proyecto (no un
placeholder) — pero "palabra" abajo son nombres en ESPAÑOL usados solo como
placeholder de desarrollo para poder probar la conexión end-to-end con el
frontend. NO son traducciones reales al totonaco. Deben reemplazarse por el
vocabulario y audio real una vez que el asesor entregue las grabaciones
validadas por hablantes nativos — ver apps/content/services.py (pipeline de
ingesta) y el README para el flujo de moderación.

`ObjetoInteractivo` separa `palabra` (la palabra real en la lengua, contra la
que se valida la escritura del usuario) de `glosa_es` (la etiqueta en español
para la UI). Aquí abajo solo hay UN string por objeto porque, mientras no
llegue el vocabulario totonaco real, `seed_demo.py` sigue guardando el mismo
placeholder en ambos campos. El día que llegue contenido real, `palabra` se
actualiza a la palabra totonaca y `glosa_es` se queda con esta glosa en
español — no hay que tocar esta lista hasta entonces.

sprite_key sigue la convención "<item>_<variante>" acordada con Raices-Front,
resuelta contra su texture atlas de Kenney Furniture Kit (CC0). "cortina" y
"reloj" no tienen sprite en el kit, así que el frontend los reemplazó por
"planta" y "ventana" en Sala — ver public/assets/sprites/furniture/CREDITS.md
en Raices-Front para el mapeo completo. Por esa misma razón, "Recámara" evita
"cortina" desde el inicio en vez de repetir el mismo problema.

Los sprite_key de "Recámara" fueron confirmados por Raices-Front contra el
Kenney Furniture Kit real (commit d5abead ahí): bed_a, pillow_a, mirror_a,
lamp_table_a, nightstand_a, dresser_a y window_a están en uso tal cual.
Excepción: "wardrobe_a" (ropero) NO tiene sprite real en el kit — el
Furniture Kit no trae ningún armario/clóset alto, solo gabinetes bajos de
cocina/baño/TV/buró. El frontend renderiza esto como placeholder gris sin
romper nada; el orquestador está buscando una fuente CC0 adicional. El
string "wardrobe_a" se queda como está hasta que exista un sprite real que
reemplazarlo tenga sentido — cambiarlo ahora sin un sprite confirmado solo
movería el problema. "ventana" reutiliza el mismo sprite_key "window_a" que
Cocina/Sala a propósito: mismo objeto, mismo atlas frame, independientemente
del cuarto. "lampara" reutiliza la misma palabra que en Sala (incluso genera
el mismo audio placeholder) pero con un sprite_key distinto ("lamp_table_a"
vs. "lamp_floor_a" en Sala) porque son objetos visualmente distintos aunque
compartan nombre en español.

Cada escena declara su `codigo` (slug) explícitamente en vez de derivarlo de
`nombre` — "Recámara" es justo el caso que rompe un `nombre.lower()` ingenuo,
porque "á" no es un carácter válido de SlugField.

"Baño" (2026-09, confirmado por Raices-Front, commit 7e83872 ahí): igual que
"ropero", "toalla" no tenía sprite disponible en el kit (no es un pack de
sanitarios) — se reemplazó por "gabinete" (`cabinet_a`,
Side/bathroomCabinet.png) en vez de esperar un asset CC0 externo, a
diferencia del caso de "ropero" que sigue pendiente. Los otros 5
(lavabo/inodoro/regadera/tina/espejo) sí tienen sprite real desde el inicio.

"Estudio" (2026-09, confirmado por Raices-Front antes de sembrar): "impresora"
no tiene sprite en el kit (no trae electrónica de oficina como impresoras o
archiveros) — se reemplazó por una segunda "planta" con sprite_key distinto
("plant_small_a", una planta de escritorio pequeña) en vez de la "planta" de
piso de Sala ("plant_a"). "librero" y "lampara" sí reutilizan exactamente el
mismo sprite_key ya usado en Sala/Recámara (bookshelf_a, lamp_table_a)
porque son el mismo objeto visual.

La "silla" del Estudio también llevaba sprite_key propio por esa misma
lógica ("office_chair_a", de oficina con ruedas, frente a "chair_a" la del
comedor), pero eso dejó de ser cierto el 2026-10-30: ahora usa "chair_a"
igual que el comedor (ver la nota en la propia fila). Se deja escrito aquí
porque esta sección explicaba el criterio contrario y una prosa que
describe el estado presente tiene que corregirse cuando el estado cambia,
no quedarse como registro de lo que ya no es.


--- AMPLIACION 2026-10: de 36 objetos a los que hay hoy, y `glosa_es` deja
--- de ser el slug
---

NO SE ESCRIBEN AQUI LOS CONTEOS. Esta seccion decia "de 36 a 108 objetos" y
"73 de los 108 no tienen sprite", y ninguna de las dos cifras era cierta:
el 108 venia del numero de etiquetas del recorrido 3D del frontend, no de
esta lista, que tiene 102 filas. Esa cifra equivocada se cito despues como
tamano del catalogo de vocabulario y contribuyo a que la tesis afirmara 109
terminos; el numero defendible era otro. Para que no vuelva a pasar, los
conteos se DERIVAN de los datos con conteos() (abajo) y los verifica
apps/content/tests/test_seed_data.py -- si alguien agrega vocabulario, la
prueba falla y obliga a actualizar la cifra a conciencia en vez de dejar
una vieja envejeciendo en un comentario que nadie vuelve a derivar.

Medido contra la API corriendo cuando se hizo la ampliacion: de las
etiquetas que el recorrido 3D ensena, solo 28 resolvian contra un objeto.
Dos causas distintas:

1. FALTABAN ESCENAS Y PALABRAS. El mundo caminable tiene ocho recintos --
   los cinco cuartos mas patio, corral y huerto -- y aqui solo habia cinco.
   Las 32 piezas de fuera (vaca, burro, maiz, temazcal, metate...) tenian
   puntero y audio en el mundo, pero `markDescubierto` devolvia 404 y el
   intento de escritura contestaba "validacion no disponible": practicar
   ahi no sumaba nada. Y dentro de la casa tambien faltaban: la cocina
   ensena 19 palabras y aqui habia 8.

2. LAS QUE SI EXISTIAN TAMPOCO EMPAREJABAN TODAS. El frontend busca su
   objeto comparando `glosa_es` con la etiqueta del punto (resolveHotspot
   en hotspots.ts), y la etiqueta es la palabra en espanol DE VERDAD, con
   acentos y espacios: "sofa" no es "sofá", "mesa_centro" no es "mesa de
   centro". Ocho de los 36 objetos sembrados fallaban solo por eso.

De ahi que cada objeto sea ahora una TERNA (palabra, glosa_es, sprite_key)
en vez de un par. Los dos primeros campos ya no son el mismo string, y la
separacion es la que el modelo siempre describio:

  * `palabra` sigue siendo el SLUG sin acentos (sofa, mesa_centro, maiz).
    Es la clave por escena, es el nombre del archivo de audio placeholder,
    y es lo que se compara contra lo que teclea el alumno. Tiene que poder
    TECLEARSE con el teclado del proyecto, que es el alfabeto totonaco
    (INALI/UV) y no tiene vocales acentuadas: "sofá" seria imposible de
    escribir ahi, "sofa" no.
  * `glosa_es` es la etiqueta que se MUESTRA, con su ortografia real en
    espanol, y es por la que el frontend empareja.

Sigue siendo placeholder: `palabra` guarda espanol, no totonaco. Lo que
cambia es que ahora las palabras del mundo caminable tienen fila y puntuan.

SPRITES: la mayoria de estas claves no tienen sprite en el Kenney Furniture
Kit, que es un kit de muebles y no trae metate, comal, temazcal ni animales.
Llevan una clave descriptiva que todavia no existe ("metate_a"), y el modo
2D los dibuja como recuadro etiquetado -- el mismo trato que "ropero" lleva
desde el principio. Es honesto: la palabra existe en el temario aunque no
haya arte. Si alguna vez molesta, la decision es del 2D, no de estos datos.
Medido el 2026-10-27 contra los .png reales de Raices-Front: 74 de las 102
filas. No se verifica aqui a proposito -- depende del arbol de archivos de
OTRO repo, que no existe en el entorno de pruebas de este; de ahi la fecha.
"""

ESCENAS_SEED = {
    "cocina": {
        "nombre": "Cocina",
        "objetos": [
            ("ventana", "ventana", "window_a"),
            # "estufa" y "refrigerador" salieron del temario el 2026-10-31
            # (decision de Alan, caminando por la cocina). Mismo caso que
            # "computadora" en el Estudio y por la misma razon: no es un
            # anacronismo que contradiga la fuente -- las descripciones
            # contemporaneas de Huehuetla si recogen la cocina de humo
            # conviviendo con el equipo comprado -- es COMPOSICION. Con el
            # fogon, el metate, el comal y el zarzo a dos metros, dos
            # electrodomesticos blancos eran lo primero que se veia al
            # entrar y se comian el cuarto.
            #
            # Sus filas NO desaparecen: seed_demo marca RETIRADO todo lo
            # que ya no esta en esta lista, asi que el progreso de quien
            # las hubiera practicado sobrevive por si vuelven.
            #
            # Hay que quitarlas AQUI y no solo en Blender: una palabra
            # sembrada sin pieza en el mundo 3D es un puntero que nunca
            # aparece, y anclajes.test.ts lo reporta como fallo -- de
            # hecho fallo, y por eso se toco esto.
            ("mesa", "mesa", "table_a"),
            ("silla", "silla", "chair_a"),
            ("metate", "metate", "metate_a"),
            ("metlapil", "metlapil", "metlapil_a"),
            ("molcajete", "molcajete", "molcajete_a"),
            ("tejolote", "tejolote", "tejolote_a"),
            ("fogon", "fogón", "fogon_a"),
            ("horno", "horno", "horno_a"),
            ("cantaro", "cántaro", "cantaro_a"),
            ("olla", "olla", "olla_a"),
            ("jarro", "jarro", "jarro_a"),
            ("chiquihuite", "chiquihuite", "chiquihuite_a"),
            ("costal", "costal", "costal_a"),
            ("comal", "comal", "comal_a"),
            ("plato", "plato", "plate_a"),
            ("vaso", "vaso", "cup_a"),
        ],
    },
    "sala": {
        "nombre": "Sala",
        "objetos": [
            ("ventana", "ventana", "window_a"),
            ("sofa", "sofá", "sofa_a"),
            ("librero", "librero", "bookshelf_a"),
            ("mesa_centro", "mesa de centro", "table_coffee_a"),
            ("lampara", "lámpara", "lamp_floor_a"),
            # "televisor" salio del temario el 2026-10-31, el mismo dia y
            # por la misma razon que "estufa" y "refrigerador" de Cocina:
            # no contradice a la fuente -- una casa de Huehuetla hoy tiene
            # television -- pero se comia el centro de una Sala que ya
            # estaba sobrecargada. Tercera palabra que sale por
            # COMPOSICION y no por documentacion, tras "computadora".
            # Marcada RETIRADO por seed_demo, no borrada. Temario: 98.
            ("planta", "planta", "plant_a"),
            ("banco", "banco", "banco_a"),
            ("cortina", "cortina", "cortina_a"),
            ("escoba", "escoba", "escoba_a"),
            ("imagen_religiosa", "imagen religiosa", "imagen_religiosa_a"),
            ("repisa", "repisa", "repisa_a"),
            ("altar", "altar", "altar_a"),
            ("vela", "vela", "vela_a"),
            ("cojin", "cojín", "cushion_a"),
        ],
    },
    "recamara": {
        "nombre": "Recámara",
        "objetos": [
            ("ventana", "ventana", "window_a"),
            ("cama", "cama", "bed_a"),
            ("buro", "buró", "nightstand_a"),
            ("lampara", "lámpara", "lamp_table_a"),
            ("ropero", "ropero", "wardrobe_a"),
            ("espejo", "espejo", "mirror_a"),
            ("cajonera", "cajonera", "dresser_a"),
            ("hamaca", "hamaca", "hamaca_a"),
            ("baul", "baúl", "baul_a"),
            ("petate", "petate", "petate_a"),
            ("sarape", "sarape", "sarape_a"),
            ("almohada", "almohada", "pillow_a"),
            ("rebozo", "rebozo", "rebozo_a"),
        ],
    },
    # EL BAÑO ES EL UNICO CUARTO DONDE LA AMPLIACION DE OCTUBRE REEMPLAZO
    # EN VEZ DE SUMAR, Y FUE A PROPOSITO. Se quitaron lavabo, inodoro,
    # regadera, tina y gabinete (espejo sobrevive, en Recamara).
    #
    # Motivo, de la investigacion etnografica que guia el recorrido 3D:
    # la casa rural totonaca NO TIENE BAÑO DENTRO. Kelly y Palerm, "The
    # Tajin Totonac" (Smithsonian ISA Pub. 13, 1952, campo 1947-49)
    # describen el aseo fuera de la casa y la ausencia de instalacion
    # hidraulica; no hay red de agua ni drenaje que sostengan un inodoro
    # de tanque ni una regadera. Esas cinco piezas no eran "sin
    # documentar" como el escritorio o el sofa, que se quedaron con una
    # advertencia escrita: CONTRADECIAN a la fuente. Esa es la distincion
    # con la que se decidio cada cuarto.
    #
    # Lo que las sustituye es el aseo documentado: balde, jicara, jabon,
    # peine, cepillo, toalla, palangana, estropajo y letrina.
    #
    # ESTA NOTA EXISTE PORQUE FALTABA. La razon vivia solo en el lado del
    # 3D (blender-pipeline/build_room_bano.py, nota larga en poblar()), y
    # desde aqui el recorte parecia una regresion -- otra sesion lo
    # reporto como tal, con razon. Si alguien vuelve a leer esto como un
    # error, no lo es.
    "bano": {
        "nombre": "Baño",
        "objetos": [
            ("balde", "balde", "balde_a"),
            ("jicara", "jícara", "jicara_a"),
            ("jabon", "jabón", "jabon_a"),
            ("peine", "peine", "peine_a"),
            ("cepillo", "cepillo", "cepillo_a"),
            ("toalla", "toalla", "toalla_a"),
            ("palangana", "palangana", "palangana_a"),
            ("estropajo", "estropajo", "estropajo_a"),
            ("letrina", "letrina", "letrina_a"),
        ],
    },
    "estudio": {
        "nombre": "Estudio",
        "objetos": [
            ("escritorio", "escritorio", "desk_a"),
            # "computadora" salio del temario el 2026-10-30 (decision de Alan).
            # No es anacronismo documental sino composicion: la pantalla era la
            # pieza que hacia leer el cuarto como oficina moderna en vez de como
            # el cuarto de trabajo de una casa rural. El escritorio y la silla se
            # quedan, con su advertencia de fuente escrita -- no estan
            # documentados, pero tampoco contradicen a la fuente, que es la misma
            # distincion con la que se podo el Bano (ver la nota de "bano").
            # Su fila NO desaparece de la base: seed_demo la marca RETIRADO, asi
            # que el progreso de quien la hubiera practicado sobrevive por si
            # vuelve. Es la primera palabra que sale del temario desde que ese
            # mecanismo existe.
            ("librero", "librero", "bookshelf_a"),
            # chair_a, el mismo sprite que la silla del comedor, a proposito:
            # era "office_chair_a" (giratoria con ruedas) y el 3D ya cambio su
            # modelo a una de madera por la misma composicion que saco la
            # computadora, asi que el 2D guardaba el criterio contrario. Que las
            # dos sillas de la casa se dibujen igual es cierto -- en el 3D
            # tambien comparten modelo -- y la razon del Sprint 14 para
            # distinguirlas (que una era de oficina) dejo de existir.
            ("silla", "silla", "chair_a"),
            ("lampara", "lámpara", "lamp_table_a"),
            ("planta", "planta", "plant_small_a"),
            ("maquina_coser", "máquina de coser", "maquina_coser_a"),
            ("malacate", "malacate", "malacate_a"),
            ("hilo", "hilo", "hilo_a"),
            ("aguja", "aguja", "aguja_a"),
            ("tijeras", "tijeras", "tijeras_a"),
            ("telar_cintura", "telar de cintura", "telar_cintura_a"),
            ("tambor", "tambor", "tambor_a"),
            ("flauta", "flauta", "flauta_a"),
        ],
    },
    "patio": {
        "nombre": "Patio",
        "objetos": [
            ("temazcal", "temazcal", "temazcal_a"),
            ("pozo", "pozo", "pozo_a"),
            ("lavadero", "lavadero", "lavadero_a"),
            ("batea", "batea", "batea_a"),
            ("lena", "leña", "lena_a"),
            ("huacal", "huacal", "huacal_a"),
            ("guaje", "guaje", "guaje_a"),
            ("mecapal", "mecapal", "mecapal_a"),
            ("tronco", "tronco", "tronco_a"),
        ],
    },
    "corral": {
        "nombre": "Corral",
        "objetos": [
            ("cabra", "cabra", "cabra_a"),
            ("guajolote", "guajolote", "guajolote_a"),
            ("nidal", "nidal", "nidal_a"),
            ("gallinero", "gallinero", "gallinero_a"),
            ("cerdo", "cerdo", "cerdo_a"),
            ("chiquero", "chiquero", "chiquero_a"),
            ("otate", "otate", "otate_a"),
            ("pesebre", "pesebre", "pesebre_a"),
            ("vaca", "vaca", "vaca_a"),
            ("burro", "burro", "burro_a"),
        ],
    },
    "huerto": {
        "nombre": "Huerto",
        "objetos": [
            ("maiz", "maíz", "maiz_a"),
            ("frijol", "frijol", "frijol_a"),
            ("calabaza", "calabaza", "calabaza_a"),
            ("espantapajaros", "espantapájaros", "espantapajaros_a"),
            ("coa", "coa", "coa_a"),
            ("arbol", "árbol", "arbol_a"),
            ("platano", "plátano", "platano_a"),
            ("naranja", "naranja", "naranja_a"),
            ("limon", "limón", "limon_a"),
            ("cafe", "café", "cafe_a"),
            ("chile", "chile", "chile_a"),
            ("vainilla", "vainilla", "vainilla_a"),
            ("tule", "tule", "tule_a"),
        ],
    },
}


def conteos() -> dict[str, int]:
    """Los conteos de esta semilla, DERIVADOS de los datos.

    Existe para que nadie vuelva a escribir una de estas cifras a mano en un
    comentario, en un README ni en la tesis: la unica que estuvo escrita a
    mano ("108 objetos") era falsa, nadie la volvio a derivar en semanas, y
    acabo citada como tamano del catalogo de vocabulario. Lo verifica
    apps/content/tests/test_seed_data.py.

    Ojo con `filas` vs `palabras_unicas`: una palabra que aparece en varios
    cuartos (ventana, lampara, silla, librero, planta) son varias filas de
    ObjetoInteractivo pero un solo termino de vocabulario. Confundirlas es
    justo el error que infla un catalogo.
    """
    filas = [(p, g, s) for datos in ESCENAS_SEED.values() for p, g, s in datos["objetos"]]
    return {
        "escenas": len(ESCENAS_SEED),
        "filas": len(filas),
        "palabras_unicas": len({g for _, g, _ in filas}),
        "sprite_keys_unicas": len({s for _, _, s in filas}),
    }


def palabras_unicas() -> list[str]:
    """Los slugs, que es lo que nombra cada archivo de audio placeholder."""
    return sorted({palabra for datos in ESCENAS_SEED.values() for palabra, _, _ in datos["objetos"]})


def glosa_de(palabra: str) -> str:
    """La etiqueta en espanol de un slug, para DECIRLA en el TTS.

    El generador de audio le pasaba a `say` el propio slug, y eso se oye:
    "imagen_religiosa" lleva un guion bajo que la voz lee o deletrea, y
    "espantapajaros" sin acento desplaza la silaba tonica -- el TTS espanol
    acentua donde dice la ortografia, no donde deberia. El archivo se sigue
    llamando por el slug (es la clave y la URL), pero lo que se PRONUNCIA es
    la glosa.
    """
    for datos in ESCENAS_SEED.values():
        for slug, glosa, _ in datos["objetos"]:
            if slug == palabra:
                return glosa
    return palabra
