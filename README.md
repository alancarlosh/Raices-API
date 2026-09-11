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
`http://127.0.0.1:8000`). Solo funciona en macOS (`say` no existe en Linux) —
su salida vive committeada en `apps/content/fixtures/audio_placeholder/`, y
`load_placeholder_audio_fixtures` (portable, sin `say` ni ffmpeg) es lo que
copia esos archivos a `MEDIA_ROOT` en CI/Render. Si cambias las palabras del
seed, corre `generate_placeholder_audio` de nuevo en tu Mac y committea el
resultado actualizado en ese directorio de fixtures.

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

## Despliegue en Render

Render free tier (2026): web service + PostgreSQL sin tarjeta, se duerme tras
15 min de inactividad — aceptable para una demo de tesis, no para producción
real con usuarios activos todo el tiempo.

**Decisión deliberada sobre el filesystem efímero de Render**: cada deploy
(y cada vez que el servicio se duerme/despierta) puede perder cualquier
archivo escrito en disco que no esté en git. En vez de resolver esto con
almacenamiento persistente o S3 (fuera de alcance por ahora), el build
command reconstruye todo lo necesario desde código + fixtures committeados
en cada deploy: migra la base, copia el audio placeholder committeado a
`MEDIA_ROOT`, y corre el seed — los tres son idempotentes, así que repetirlos
en cada deploy no duplica ni corrompe nada. Cuando el audio real llegue y se
sirva desde un CDN (el plan original, ver más abajo), este problema
desaparece solo porque `MEDIA_ROOT` deja de importar en producción.

### Pasos para Alan

0. Si el repo no está en GitHub todavía: crear un repo y hacer push de esta
   rama (`git remote add origin <url> && git push -u origin main`). Render
   necesita conectarse a un repo de GitHub, no puede desplegar un working
   directory local.
1. Crear cuenta en [render.com](https://render.com) (login con GitHub, sin
   tarjeta).
2. **New +** → **Blueprint** → conectar el repo `Raices-API`. Render detecta
   `render.yaml` en la raíz y propone crear el web service (`raices-api`) y
   la base de datos (`raices-db`) juntos — aceptar.
3. Variables de entorno a llenar en el dashboard del web service (las que
   `render.yaml` marca como manuales, el resto —`SECRET_KEY`,
   `DATABASE_URL`— Render las genera/conecta solo):
   - `ALLOWED_HOSTS`: dejar vacío en el primer deploy (o poner un valor
     cualquiera temporal); Render ya inyecta automáticamente
     `RENDER_EXTERNAL_HOSTNAME` como host permitido además de lo que pongas
     aquí, pero conviene fijarlo explícito una vez que se conozca la URL real
     (paso 5) — ver nota de verificación abajo.
   - `CORS_ALLOWED_ORIGINS`: la URL del frontend en Cloudflare Pages una vez
     que exista (ej. `https://raices-front.pages.dev`). Vacío rompe CORS para
     el frontend real, pero no bloquea probar la API sola con curl/Postman.
   - `MEDIA_BASE_URL`: la URL pública que Render asigna al servicio (paso 5),
     ej. `https://raices-api.onrender.com` — sin esto, `audio_ogg`/`audio_m4a`
     en las respuestas apuntarían a `127.0.0.1`, que no significa nada fuera
     de esta máquina.
   - `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` /
     `DJANGO_SUPERUSER_EMAIL`: credenciales del admin de Django en producción
     (para entrar a `/admin/` y aprobar/rechazar contenido moderado). El build
     los usa para crear ese usuario automáticamente en cada deploy — ver
     `apps/accounts/management/commands/ensure_superuser.py`. Usar una
     contraseña real, no la de desarrollo; si se omiten estas tres variables
     el build sigue sin romperse, solo no habrá superusuario.
4. Deploy. La primera vez tarda más (instala dependencias, corre
   `collectstatic`, migra, siembra datos, crea el superusuario).
5. Una vez arriba, Render muestra la URL pública real del servicio
   (`https://<algo>.onrender.com`). Volver al paso 3 y completar
   `ALLOWED_HOSTS`/`MEDIA_BASE_URL`/`CORS_ALLOWED_ORIGINS` con esa URL real, y
   disparar un redeploy manual ("Manual Deploy" → "Deploy latest commit").
6. Avisarle a Claude la URL real para ajustar CORS del lado del código si
   hace falta y coordinar con el frontend.

**Nota de verificación**: que Render inyecte `RENDER_EXTERNAL_HOSTNAME`
automáticamente es una conveniencia de su plataforma que el código ya
aprovecha (ver `config/settings.py`) pero que no verifiqué con una fuente
externa actualizada a 2026 — trátalo como una red de seguridad adicional, no
como sustituto de fijar `ALLOWED_HOSTS` explícito en el paso 5.

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

- `POST /api/registro/` — registro real de usuarios (no requiere auth). Body
  `{"username": "...", "password": "...", "email": "..."}` (`email` opcional).
  El rol nunca se acepta como input: todo usuario nuevo entra como `aprendiz`;
  asignar `hablante_revisor`/`admin` es una acción manual desde el admin de
  Django. La contraseña pasa por los validadores estándar de Django (longitud
  mínima, no común, no solo numérica). Responde `201` con `{"user": {...},
  "access": "...", "refresh": "..."}` — mismo shape de tokens que
  `POST /api/token/`, así que el frontend puede dejar al usuario autenticado
  de una vez sin una segunda llamada a login. Limitado a 10 intentos/min por
  IP (`ScopedRateThrottle`, scope `"registro"`) — responde `429` si se excede.
- `POST /api/token/` / `POST /api/token/refresh/` — JWT (login normal para
  usuarios ya registrados). `POST /api/token/` limitado a 10 intentos/min por
  IP (scope `"token_obtain"`) contra fuerza bruta de contraseñas; `refresh`
  no tiene límite propio. Nota: el límite es por worker de gunicorn
  (`LocMemCache` no es compartido entre procesos) — suficiente con el worker
  único por defecto de Render free tier, no escala tal cual a varios workers
  sin pasar a un caché compartido (Redis).
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
