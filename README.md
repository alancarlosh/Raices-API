# Raíces API

Backend (Django + DRF) de "Raíces": plataforma para enseñanza y práctica de lenguas
originarias mediante un videojuego 2D de exploración de una casa. Ver el repo hermano
`Raices-Front` (React + Phaser) para el cliente.

## Setup local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Por defecto usa SQLite. Para PostgreSQL define `DATABASE_URL` en `.env`.

CORS ya está habilitado (`django-cors-headers`) para `http://localhost:5173` y
`http://localhost:8080` (orígenes típicos de un dev server de Vite); ajusta
`CORS_ALLOWED_ORIGINS` en `.env` si el frontend corre en otro puerto.

### Datos de prueba

```bash
python manage.py generate_placeholder_audio   # TTS local (macOS say + ffmpeg), una sola vez
python manage.py seed_demo
```

Crea la lengua "Totonaco" (`toto`) — confirmada como la primera lengua objetivo
real del proyecto, no un placeholder — con dos escenas ("Cocina" y "Sala") de
8 objetos publicados cada una, y un usuario de prueba (`demo` / `Demo12345!`)
para que el frontend pueda obtener un JWT real vía `POST /api/token/`. Ambos
comandos son idempotentes. Lo que sí sigue siendo placeholder son las
**palabras** sembradas (en español, ej. "silla", "mesa") — deben reemplazarse
por vocabulario totonaco real validado por el asesor/hablantes nativos en
cuanto esté disponible.

`generate_placeholder_audio` genera clips TTS (voz "Paulina", NO grabaciones
reales) en OGG+M4A con `say` + ffmpeg y los guarda en `media/audio/placeholder/`,
servidos localmente por Django en `/media/...` — así el audio funciona de
verdad en desarrollo sin depender de un CDN real. `MEDIA_BASE_URL` en `.env`
debe coincidir con el host:puerto donde corre `runserver` (por defecto
`http://127.0.0.1:8000`).

### Pipeline de ingesta de audio real

```bash
python manage.py ingest_audio <objeto_id> <ruta/al/audio/fuente.wav>
```

Es el comando que se usará cuando lleguen las grabaciones reales del asesor:
genera `audio_ogg`/`audio_m4a` con ffmpeg a partir del archivo fuente, los
guarda en `media/audio/ingerido/`, y deja el objeto en estado `en_revision`
(desaparece de `GET /api/escenas/<id>/`, que solo expone `publicado`) hasta
que un hablante-revisor lo apruebe desde el admin de Django (acción "Marcar
como publicado" en `ObjetoInteractivoAdmin`). Nunca publica automáticamente.

## Estructura

Patrón **Services + Selectors** (Django Styleguide de HackSoft): `models.py` solo
estructura, `selectors.py` consultas de solo lectura, `services.py` lógica de negocio
y escritura, `views.py` delgadas (solo orquestan).

- `apps/accounts` — usuario custom con rol (aprendiz / hablante_revisor / admin), JWT.
- `apps/languages` — catálogo de lenguas originarias.
- `apps/content` — `Escena` (cuarto) → `ObjetoInteractivo`, con flujo de moderación
  (borrador / en_revision / publicado) vía el admin de Django.
- `apps/progress` — `ProgresoUsuario` (objetos descubiertos) e `IntentoEscritura`
  (histórico de intentos de escritura).

**Restricción lingüística crítica:** la validación de escritura normaliza ambos
strings a Unicode NFC antes de comparar, pero nunca usa `unidecode` ni elimina
diacríticos — el saltillo (Ꞌ) y las vocales largas cambian el significado de la
palabra en varias lenguas originarias. Ver `apps/progress/services.py`.

## Endpoints

- `POST /api/token/` / `POST /api/token/refresh/` — JWT.
- `GET /api/escenas/` — listado ligero (`id`, `codigo`, `nombre`, `lengua`, `orden`)
  para que el frontend arme su grafo de navegación entre cuartos sin hardcodear
  ids numéricos; referencia cada escena por su `codigo` (slug estable, ej.
  `"cocina"`) y resuelve el `id` real desde aquí.
- `GET /api/escenas/<id>/` — escena con sus objetos publicados (cacheada 15 min).
  Cada objeto expone `audio_ogg` y `audio_m4a`: Safari/iOS no soporta Ogg de forma
  confiable (solo Opus empacado en CAF), así que cada audio se sirve en dos
  formatos y el frontend debe usar múltiples `<source>` con fallback.
  Cada objeto expone `sprite_key` en vez de una imagen: los sprites viven en un
  texture atlas empacado en `Raices-Front` (assets CC0 tipo Kenney Furniture
  Kit), el backend solo manda la clave para resolverlo del lado del cliente.
- `POST /api/objetos/<id>/descubrir/` — marca un objeto como descubierto.
- `POST /api/objetos/<id>/intento-escritura/` — body `{"texto_ingresado": "..."}`.
- `GET /api/progreso/` — % de objetos descubiertos por escena.

## Tests

```bash
python -m pytest
```
