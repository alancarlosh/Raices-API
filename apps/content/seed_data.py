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
"planta" y "ventana" — ver public/assets/sprites/furniture/CREDITS.md en
Raices-Front para el mapeo completo.
"""

ESCENAS_SEED = {
    "Cocina": [
        ("silla", "chair_a"),
        ("mesa", "table_a"),
        ("puerta", "door_a"),
        ("ventana", "window_a"),
        ("estufa", "stove_a"),
        ("refrigerador", "fridge_a"),
        ("plato", "plate_a"),
        ("vaso", "cup_a"),
    ],
    "Sala": [
        ("sofa", "sofa_a"),
        ("mesa_centro", "table_coffee_a"),
        ("lampara", "lamp_floor_a"),
        ("televisor", "tv_modern_a"),
        ("planta", "plant_a"),
        ("cojin", "cushion_a"),
        ("librero", "bookshelf_a"),
        ("ventana", "window_a"),
    ],
}


def palabras_unicas() -> list[str]:
    return sorted({palabra for objetos in ESCENAS_SEED.values() for palabra, _ in objetos})
