"""Datos de fixture compartidos entre `seed_demo` y `generate_placeholder_audio`.

ADVERTENCIA: el totonaco YA ES la lengua real confirmada del proyecto (no un
placeholder) — pero "palabra" abajo son nombres en ESPAÑOL usados solo como
placeholder de desarrollo para poder probar la conexión end-to-end con el
frontend. NO son traducciones reales al totonaco. Deben reemplazarse por el
vocabulario y audio real una vez que el asesor entregue las grabaciones
validadas por hablantes nativos — ver apps/content/services.py (pipeline de
ingesta) y el README para el flujo de moderación.

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
piso de Sala ("plant_a"). Igual patrón para "silla": reutiliza la palabra de
Cocina pero con sprite_key distinto ("office_chair_a", silla de oficina con
ruedas, vs. "chair_a" la silla de comedor). "librero" y "lampara" sí
reutilizan exactamente el mismo sprite_key ya usado en Sala/Recámara
(bookshelf_a, lamp_table_a) porque son el mismo objeto visual.
"""

ESCENAS_SEED = {
    "cocina": {
        "nombre": "Cocina",
        "objetos": [
            ("silla", "chair_a"),
            ("mesa", "table_a"),
            ("puerta", "door_a"),
            ("ventana", "window_a"),
            ("estufa", "stove_a"),
            ("refrigerador", "fridge_a"),
            ("plato", "plate_a"),
            ("vaso", "cup_a"),
        ],
    },
    "sala": {
        "nombre": "Sala",
        "objetos": [
            ("sofa", "sofa_a"),
            ("mesa_centro", "table_coffee_a"),
            ("lampara", "lamp_floor_a"),
            ("televisor", "tv_modern_a"),
            ("planta", "plant_a"),
            ("cojin", "cushion_a"),
            ("librero", "bookshelf_a"),
            ("ventana", "window_a"),
        ],
    },
    "recamara": {
        "nombre": "Recámara",
        "objetos": [
            ("cama", "bed_a"),
            ("almohada", "pillow_a"),
            ("ropero", "wardrobe_a"),
            ("espejo", "mirror_a"),
            ("lampara", "lamp_table_a"),
            ("buro", "nightstand_a"),
            ("cajonera", "dresser_a"),
            ("ventana", "window_a"),
        ],
    },
    "bano": {
        "nombre": "Baño",
        "objetos": [
            ("lavabo", "sink_a"),
            ("inodoro", "toilet_a"),
            ("regadera", "shower_a"),
            ("tina", "bathtub_a"),
            ("espejo", "mirror_a"),
            ("gabinete", "cabinet_a"),
        ],
    },
    "estudio": {
        "nombre": "Estudio",
        "objetos": [
            ("escritorio", "desk_a"),
            ("computadora", "computer_a"),
            ("silla", "office_chair_a"),
            ("librero", "bookshelf_a"),
            ("lampara", "lamp_table_a"),
            ("planta", "plant_small_a"),
        ],
    },
}


def palabras_unicas() -> list[str]:
    return sorted({palabra for datos in ESCENAS_SEED.values() for palabra, _ in datos["objetos"]})
