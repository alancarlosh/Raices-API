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
cuanto esté disponible. `ObjetoInteractivo` ya distingue `palabra` (la palabra
real en la lengua, contra la que se valida la escritura — ver
`apps/progress/services.py`) de `glosa_es` (la etiqueta en español para la
UI); el seed llena ambos campos con el mismo placeholder mientras no exista
vocabulario totonaco real que reemplace solo `palabra`.

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

## Antes de una prueba de campo

Un salón entero entrando a la vez no es el caso para el que está dimensionado
el plan gratuito. Lo medido en producción, que es lo que manda:

| | |
|---|---|
| 404 (sin hash, sin base de datos) | 0,15 s |
| Lectura de base de datos | 0,14 s |
| Un login o registro | ~1,1 s (eran 1,96 s antes de bajar las iteraciones) |
| Primera petición con el servicio dormido | **34 s** |

Y `startCommand` es `gunicorn config.wsgi:application` sin `--workers`, cuyo
defecto es **un worker sync**: una petición a la vez. El techo real son unos
55 registros por minuto, no los 90/min que permite el throttle — el cuello es
la CPU, no el límite declarado. Más workers no ayudaría: el trabajo es CPU y
el plan gratuito da una fracción de núcleo.

De ahí dos cosas que conviene hacer, las dos gratis:

1. **Despertar la API unos minutos antes**, con `./scripts/calentar.sh`. Si no,
   esos 34 s se los come el primer alumno que entre, que además no sabe que
   está esperando un arranque. El script explica por qué no se deja despierta
   con un cron: el plan da 750 horas de instancia al mes y un mes tiene 720.
2. **Que entren escalonados**, en grupos de unos diez. A ~1 s por alumno, un
   grupo de diez tarda diez segundos; sesenta de golpe hacen cola de un
   minuto. El throttle ya no los bloquea (90/min por IP, ver más abajo), pero
   la cola sigue existiendo.

### Si hacen falta sesenta a la vez: subir el plan

Lo de arriba es lo que se puede apretar sin gastar. Si la prueba necesita que
sesenta entren de verdad al mismo tiempo, el único arreglo real es más CPU, y
los números de Render son públicos:

| Plan | CPU | RAM |
|---|---|---|
| `free` (el actual) | **0,1** | 512 MB |
| `0.5c-512mb` (Starter) | **0,5** | 512 MB |
| `1c-2g` (Standard) | 1 | 2 GB |

Starter es cinco veces la CPU por la misma memoria. Como el coste del acceso es
casi todo hasheo —y eso escala con la CPU— el hasheo pasaría de ~1,06 s a
**~0,21 s**, o sea unos **280 accesos por minuto** en vez de ~50: los sesenta
alumnos entrarían en unos trece segundos. Con Standard no hace falta pagar más:
el cuello desaparece ya en Starter.

**Dos cosas que NO hay que tocar al subir el plan**, porque medirlas primero
cambia la respuesta:

- **El número de workers no se cambia en el código.** `startCommand` es
  `gunicorn config.wsgi:application` y gunicorn ya lee la variable de entorno
  `WEB_CONCURRENCY` (su valor por defecto es
  `int(os.environ.get("WEB_CONCURRENCY", 1))`), así que se ajusta desde el
  panel de Render sin desplegar nada. Con Starter vale la pena `WEB_CONCURRENCY=2`:
  no acelera el hasheo, pero evita que leer una escena haga cola detrás de él.
- **La memoria no es el problema, así que no hay que subir de plan por ella.**
  Medido en local: el master de gunicorn ocupa 19,7 MB y cada worker 46,2 MB,
  de modo que en 512 MB caben cuatro de sobra. En el plan gratuito más workers
  no servirían de nada: se repartirían la misma décima de núcleo.

### Y la base de datos, que es el riesgo mayor

Independiente del plan del servicio web, y peor: **una base Postgres gratuita de
Render caduca 30 días después de creada** (luego 14 días de gracia y se borra),
tiene 1 GB y **no admite respaldos**. La caída del 28-10-2026 fue exactamente
eso.

Si los datos de la prueba de campo son evidencia para la tesis —lo son— antes de
agendarla conviene:

1. Mirar en el panel **cuándo caduca** la base actual.
2. Correr `python manage.py respaldar` antes y después de la prueba (ver
   `restaurar` para la vuelta).
3. **Ensayar la restauración con el archivo de verdad**, no solo confiar en la
   prueba automática:

   ```
   ./scripts/ensayar_restauracion.sh respaldo_raices.json
   ```

   Monta una base SQLite desechable, siembra el catálogo, restaura ahí y
   comprueba **clave por clave** que todas las filas del respaldo llegaron —
   no por totales, porque `seed_demo` siembra una cuenta y `restaurar`
   sobrescribe por clave primaria, así que un conteo por diferencia puede
   cuadrar faltando filas. No toca producción ni tu `db.sqlite3`, y no imprime
   nada personal: solo modelos, cuentas y claves.

   Su límite, dicho en claro: producción es Postgres y el ensayo corre en
   SQLite, así que comprueba el viaje de los datos pero no descarta los fallos
   propios de Postgres (secuencias desfasadas tras escribir por PK, tipos,
   orden de restricciones). Con un Postgres local basta apuntar `DATABASE_URL`
   a él y volver a correrlo: el script lo acepta tal cual.
4. Decidir si esos datos pueden vivir en algo que se borra solo.

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
  `{"username": "...", "password": "...", "email": "..."}` — `email` es
  obligatorio y único (tanto en el serializer como ahora a nivel de base de
  datos, ver el modelo `Usuario`): lo necesita tanto `restablecer-password/`
  como el login por correo de abajo. El rol nunca se acepta como input: todo
  usuario nuevo entra como `aprendiz`;
  asignar `hablante_revisor`/`admin` es una acción manual desde el admin de
  Django. La contraseña pasa por los validadores estándar de Django (longitud
  mínima, no común, no solo numérica). Responde `201` con `{"user": {...},
  "access": "...", "refresh": "..."}` — mismo shape de tokens que
  `POST /api/token/`, así que el frontend puede dejar al usuario autenticado
  de una vez sin una segunda llamada a login. Limitado por IP en **dos
  ventanas**: 90/min (scope `"registro"`) para la ráfaga y 600/hora (scope
  `"registro_sostenido"`) contra el abuso sostenido — responde `429` si se
  excede. Los 90/min no son un redondeo: la prueba de campo son varios
  grupos de 60+ alumnos que se registran a la vez desde la única IP
  pública de la escuela, y con los 10/min que había antes, del undécimo en
  adelante recibía `429`.
- `POST /api/token/` / `POST /api/token/refresh/` — JWT (login normal para
  usuarios ya registrados). Body de `POST /api/token/`:
  `{"email": "...", "password": "..."}` — **por correo, no por username**
  (`EmailTokenObtainPairSerializer` + `EmailBackend`, ver
  `apps/accounts/serializers.py` y `apps/accounts/backends.py`;
  `USERNAME_FIELD` del modelo sigue siendo `"username"`, sin tocar — esto
  vive un nivel por encima, solo en esta vista). Limitado por IP en dos
  ventanas, 90/min (scope `"token_obtain"`) y 900/hora (scope
  `"token_obtain_sostenido"`), **más** 5/min por cuenta objetivo (scope
  `"token_obtain_por_cuenta"`, ver `apps/accounts/throttling.py`). Ese
  último es el que frena la fuerza bruta de verdad —limita los intentos
  contra un correo concreto sin importar desde cuántas IPs vengan— así
  que los topes por IP pueden ser holgados para que quepa un salón sin
  debilitarlo. `refresh` no tiene límite propio. Nota: el límite es por worker de gunicorn
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
- `GET /api/me/` — username/email/rol del usuario autenticado (a partir del
  JWT), para que el frontend no dependa de datos capturados en el momento del
  login/registro (pueden desincronizarse entre dispositivos/sesiones).
- `POST /api/verificar-email/` / `POST /api/verificar-email/confirmar/` —
  código de 6 dígitos por correo para confirmar que el usuario autenticado
  es dueño de su dirección. A diferencia de `restablecer-password/`, requiere
  sesión (`IsAuthenticated`): no hay enumeración de correos que evitar, quien
  llama ya probó ser dueño de la cuenta al iniciar sesión. El código vale 15
  minutos y se consume al primer intento correcto (uno nuevo invalida
  cualquiera anterior sin usar). `solicitar` limitado por IP, 5/min (scope
  `"verificar_email"`) **y** comparte con `restablecer-password/` el mismo
  scope sostenido (`"envio_correo_sostenido"`, 12/hora) porque las dos
  gastan el mismo cupo diario de Brevo — ver `config/settings.py`.
  `confirmar` limitado aparte, 10/min (scope `"verificar_email_confirmar"`),
  contra adivinar el código por fuerza bruta; no lleva sostenido porque no
  manda correo.
- `POST /api/objetos/<id>/descubrir/` — marca un objeto como descubierto.
- `POST /api/objetos/<id>/intento-escritura/` — body `{"texto_ingresado": "..."}`.
- `GET /api/progreso/` — `{"escenas": [...], "total": {...}}`, cada uno con
  `objetos_descubiertos`/`porcentaje` (clics) y `objetos_dominados`/
  `porcentaje_dominado`. Un objeto cuenta como "dominado" si el intento de
  escritura MÁS RECIENTE del usuario para ese objeto fue correcto — no es un
  logro permanente por acertar una vez, se deriva del historial de
  `IntentoEscritura` (ver `apps/progress/selectors.py`). Descubrir es un clic
  trivial; dominar refleja la habilidad real que enseña la plataforma.

## Tests

```bash
python -m pytest
```
