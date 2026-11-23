"""
Django settings for the Raíces project.
"""

import os
import warnings
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from config import email_backend

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    # RENDER es una env var que Render inyecta automáticamente en todo
    # servicio desplegado ahí (no algo que este proyecto define) — es la
    # señal real de "esto es producción", más confiable que DEBUG (que
    # podría estar mal configurado, aunque render.yaml ya lo fija en False).
    # Sin este chequeo, un despliegue real sin SECRET_KEY arrancaría en
    # silencio con la clave insegura de abajo en vez de fallar ruidosamente
    # (render.yaml declara SECRET_KEY con generateValue=true, así que hoy
    # nunca falta en un deploy normal, pero el código no lo garantizaba).
    # Deliberadamente NO se ata a DEBUG: correr `pytest`/`runserver` en
    # local sin ningún .env (el caso normal de este repo) debe seguir
    # funcionando con la clave de desarrollo de abajo sin fricción.
    if os.environ.get("RENDER"):
        raise ImproperlyConfigured(
            "SECRET_KEY no está definido en un despliegue de Render -- nunca "
            "debe arrancar en producción con la clave insegura de desarrollo."
        )
    SECRET_KEY = "django-insecure-dev-only-change-in-production"

# Falla cerrado: sin DEBUG explícito en el entorno, se asume producción. Dev
# local siempre define DEBUG=True en .env (ver .env.example).
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Render inyecta este env var automáticamente con el hostname público del
# servicio (ej. "raices-api.onrender.com") — se agrega solo si existe, no
# reemplaza la necesidad de configurar ALLOWED_HOSTS explícitamente.
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.accounts",
    "apps.languages",
    "apps.content",
    "apps.progress",
    "apps.telemetria",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database — SQLite por defecto para desarrollo local; define DATABASE_URL
# (p. ej. postgres://user:pass@host:5432/nombre_bd) para usar PostgreSQL.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "accounts.Usuario"

# EL COSTE DE HASHEAR, AJUSTADO A LA MAQUINA QUE LO PAGA. Ver
# apps/accounts/hashers.py para el por que con los numeros medidos en
# produccion -- resumen: ~1,8 s de cada login en el plan gratuito de
# Render son CPU hasheando, con un solo worker sync, y la prueba de campo
# son grupos de 60+ alumnos registrandose a la vez.
#
# La lista repite los demas hasheadores de Django a proposito: declarar
# PASSWORD_HASHERS sustituye la lista entera, y sin ellos se perderia la
# capacidad de verificar cualquier hash que no sea pbkdf2_sha256.
PASSWORD_HASHERS = [
    "apps.accounts.hashers.PBKDF2SeiscientosMil",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# whitenoise sirve los estáticos propios de Django (admin, DRF browsable API)
# en producción sin depender de un servidor web aparte (Render free tier no
# trae uno). Correr `collectstatic` en el build step llena STATIC_ROOT.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Audio/sprites placeholder servidos localmente vía la vista de medios propia
# en config/urls.py (no depende de DEBUG, ver comentario ahí). En producción
# el audio real lo sirve un CDN (Backblaze B2 + Cloudflare, ver README) — pero
# mientras eso no exista, Render también sirve estos placeholders desde aquí
# (ver sección "Despliegue en Render" del README sobre por qué el filesystem
# efímero de Render no es un problema para este caso).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_BASE_URL = os.environ.get("MEDIA_BASE_URL", "http://127.0.0.1:8000")


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # Límite básico contra fuerza bruta/registro en bucle en /api/token/ y
    # /api/registro/ ahora que la API vive en una URL pública (ver
    # apps/accounts/views.py). Nota de alcance: el caché por defecto es
    # LocMemCache (proceso único), así que el límite es por worker de
    # gunicorn, no global — suficiente para un solo worker (el caso actual en
    # Render free tier), no para escalar a varios sin un caché compartido
    # (Redis) más adelante.
    # DOS VENTANAS POR IP: la del minuto cubre la RAFAGA de un salon
    # entrando junto; la de la hora acota el abuso sostenido. Ver
    # RealIpSostenidoScopedRateThrottle en apps/accounts/throttling.py.
    #
    # EL NUMERO SALE DE UN CASO REAL, no de un redondeo: la prueba de
    # campo son varios grupos de 60+ alumnos que se REGISTRAN ahi mismo,
    # todos desde la unica IP publica de la escuela. Con los 10/min que
    # habia antes, del undecimo en adelante recibia 429 -- o sea que la
    # prueba se bloqueaba sola, y el sintoma que habria visto Alan es
    # "a mis alumnos no les deja entrar", sin nada en el front que lo
    # explicara.
    #
    # Lo que NO se toca es token_obtain_por_cuenta: ese es el que frena
    # la fuerza bruta de verdad y subir los de IP no lo debilita.
    "DEFAULT_THROTTLE_RATES": {
        "registro": "90/min",
        # 600/hora: cuatro grupos de 60 en una manana caben de sobra, y
        # deja un tope a la creacion de cuentas basura, que ademas
        # ensuciaria una base de datos que esta en el plan gratuito.
        "registro_sostenido": "600/hour",
        "token_obtain": "90/min",
        # Mas holgado que el de registro porque entrar se repite y
        # registrarse no: un alumno que recarga, se le caduca el token o
        # vuelve al dia siguiente pide otro.
        "token_obtain_sostenido": "900/hour",
        # Por cuenta objetivo (PorCuentaScopedRateThrottle, ver
        # apps/accounts/throttling.py), no por IP — más estricto que
        # token_obtain porque su propósito específico es frenar fuerza
        # bruta contra una sola cuenta sin importar cuántas IPs use el
        # atacante.
        "token_obtain_por_cuenta": "5/min",
        # Más estricto que registro/token_obtain: cada solicitud dispara un
        # envío de correo real, así que el abuso aquí es más costoso
        # (spam a la bandeja de alguien) que solo intentos fallidos.
        "password_reset": "5/min",
        # Mismo perfil de costo que password_reset: cada solicitud manda un
        # correo real con un código de 6 dígitos. Ver
        # SolicitarVerificacionEmailView.
        "verificar_email": "5/min",
        # Adivinar el código de 6 dígitos (1.000.000 de combinaciones) es
        # el riesgo de ESTE endpoint y no el de Brevo: 10/min por IP deja
        # pasar los typos normales y hace que agotar el espacio de
        # búsqueda tome semanas, no minutos -- y el código caduca a los 15
        # minutos de todas formas, lo que reinicia la ventana de ataque
        # mucho antes. No lleva sostenido: no envía correo, así que no
        # gasta el cupo de Brevo.
        "verificar_email_confirmar": "10/min",
        # ESTE SI NECESITA SU SOSTENIDO, y no por el mismo motivo que
        # registro/token_obtain (ahi el sostenido DA MAS margen que el de
        # ráfaga). Aquí hace falta por lo contrario: 5/min sostenido una
        # hora entera ya son 300 correos -- el cupo DIARIO gratis de
        # Brevo, entero, en una sola hora y desde una sola IP.
        #
        # COMPARTIDO A PROPOSITO entre password_reset Y verificar_email
        # (las dos usan este MISMO nombre de scope como su
        # throttle_scope_sostenido, no uno propio cada una) -- es el
        # mismo cupo de Brevo el que gastan las dos, así que sumarían:
        # con un sostenido independiente de 12/hora cada una, una sola IP
        # alternando entre las dos llegaría a 24/hora, el doble de lo que
        # el número de abajo existe para impedir. ScopedRateThrottle
        # comparte el contador cuando el string del scope es el mismo,
        # venga de la vista que venga -- es la propiedad que esto
        # aprovecha.
        #
        # 12/hora por IP, y el numero sale de abajo hacia arriba: es el
        # mayor que deja a UNA SOLA IP, sosteniendo CUALQUIER COMBINACION
        # de las dos las 24 horas del dia, por DEBAJO del cupo diario
        # entero (12*24=288 < 300). Mas alto que eso ya permitiria a una
        # sola IP agotar sola el cupo de todo el dia si insistiera sin
        # parar.
        #
        # Y es generoso de todas formas para quien no abusa: a
        # diferencia de iniciar sesion, pedir un restablecimiento o un
        # codigo de verificacion no es algo que se repita seguido, asi
        # que varias personas detras de la misma red (la de la escuela)
        # pidiendo el suyo en la misma hora caben de sobra en 12.
        #
        # Lo que esto NO cubre: un ataque repartido entre muchas IPs
        # distintas. Eso seguiria pudiendo agotar el cupo de Brevo entre
        # todas; haria falta un tope GLOBAL (no por IP) para cerrarlo del
        # todo, y no existe todavia uno asi en este proyecto para ningun
        # endpoint.
        "envio_correo_sostenido": "12/hour",
        # Telemetría de rendimiento. Generoso a propósito: el cliente manda
        # UNA medida por escena y por carga de página, así que un alumno
        # recorriendo las ocho escenas y recargando un par de veces cabe de
        # sobra. El tope está contra un bucle mal escrito en el front, no
        # contra un atacante — el endpoint ya exige sesión. Y conviene que
        # exista: la base de Render es de plan gratuito y un bucle podría
        # llenarla en una tarde de clase.
        "rendimiento": "60/hour",
    },
}

# URL pública del frontend, usada para construir el enlace de restablecer
# contraseña que se envía por correo (ver apps/accounts/services.py). Debe
# apuntar al origen real donde corre Raices-Front, sin slash final.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8080").rstrip("/")

# Envío de correo (recuperación de contraseña). Proveedor elegido por Alan:
# Brevo (SMTP transaccional, 300 correos/día gratis de forma permanente,
# smtp-relay.brevo.com). EMAIL_BACKEND sigue en 'console' por defecto (el
# correo se imprime en el log del servidor, no se envía de verdad) hasta que
# existan credenciales SMTP reales — Render no las tiene todavía, así que en
# producción esto sigue sin entregar correos hasta que se configuren las
# variables de entorno de abajo (EMAIL_BACKEND=...smtp.EmailBackend,
# EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL) con los datos de
# la cuenta Brevo de Alan. EMAIL_HOST/EMAIL_PORT/EMAIL_USE_TLS ya traen el
# default correcto para Brevo y no deberían necesitar overridearse.
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-responder@raices.local")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp-relay.brevo.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"

# Guarda contra el estado intermedio: SMTP encendido sin credenciales hace
# que send_mail reviente y, como services.py lo llama con
# fail_silently=False, "recuperar contraseña" devolvería un 500 al usuario
# en vez de su 200 de siempre. Mejor volver a consola y avisar — ver
# config/email_backend.py para el razonamiento completo y las pruebas.
#
# Se usa `warnings` y no `logging` porque esto corre al importar settings,
# antes de que LOGGING esté configurado; en Render el aviso sale igual por
# stderr, que es donde se leen los logs del servicio.
EMAIL_BACKEND, _correo_incompleto = email_backend.resolver(
    backend=EMAIL_BACKEND,
    host_user=EMAIL_HOST_USER,
    host_password=EMAIL_HOST_PASSWORD,
    from_email=DEFAULT_FROM_EMAIL,
)
if _correo_incompleto:
    warnings.warn(
        "EMAIL_BACKEND pedía SMTP pero falta "
        + ", ".join(_correo_incompleto)
        + ". Se vuelve al backend de consola: la aplicación sigue en pie y el "
        "enlace de recuperación se escribirá en el log del servidor en vez de "
        "enviarse. Completa esas variables para que salgan los correos.",
        stacklevel=2,
    )

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Sin esto, restablecer la contraseña (apps/accounts/services.py) no
    # invalida los tokens ya emitidos: un access token robado seguiría
    # funcionando hasta 1h más y un refresh token hasta 7 días más,
    # anulando el propósito del reset (cuenta comprometida -> reset -> el
    # atacante sigue adentro). CHECK_REVOKE_TOKEN mete un hash del password
    # actual del usuario en cada token emitido (for_user()) y lo revalida en
    # cada request autenticado (JWTAuthentication.get_user()) — en cuanto
    # cambia el password, TODO token emitido antes (access o refresh, y
    # cualquier access token nuevo generado a partir de un refresh viejo,
    # ya que RefreshToken.access_token copia este claim) deja de servir de
    # inmediato. Se prefiere sobre instalar rest_framework_simplejwt.token_
    # blacklist porque blacklistear solo cubre refresh tokens — un access
    # token robado seguiría vivo hasta su propia expiración de todos modos.
    "CHECK_REVOKE_TOKEN": True,
    # El mismo refresh token de 7 días servía indefinidamente hasta su
    # expiración natural — ROTATE_REFRESH_TOKENS hace que cada uso de
    # /api/token/refresh/ emita un refresh nuevo, y BLACKLIST_AFTER_ROTATION
    # (junto con rest_framework_simplejwt.token_blacklist en INSTALLED_APPS,
    # arriba) es lo que de verdad invalida el anterior — sin eso, "rotar"
    # solo emitiría uno nuevo dejando el viejo también válido, sin cerrar
    # nada. IMPORTANTE para quien consuma esto: la respuesta de
    # /api/token/refresh/ ahora incluye un campo "refresh" nuevo además de
    # "access" — el cliente debe guardar y usar ESE en vez de reutilizar el
    # que ya tenía, o su segundo refresh fallará (el viejo queda
    # blacklisteado en cuanto se usa una vez). Raices-Front's
    # refreshAccessToken() todavía no hace esto — ver el mensaje a
    # raices-front-11 del 2026-09-18/19 sobre este cambio de contrato.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Caché en memoria para desarrollo; en producción conviene apuntar a algo
# compartido (p. ej. Redis) si se corre con varios workers.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080"
    ).split(",")
    if o.strip()
]

# Endurecimiento HTTPS/cookies, solo cuando de verdad corre en Render (ver
# RENDER más abajo) -- en dev local el servidor corre en HTTP plano, así que
# SECURE_SSL_REDIRECT o las cookies "Secure" romperían runserver/el admin
# localmente. Deliberadamente NO atado a `not DEBUG`: este repo no trae un
# .env por defecto (correr `pytest`/`runserver` así en local es el flujo
# normal, ver la nota de SECRET_KEY arriba), así que DEBUG cae a False ahí
# también -- atarlo a DEBUG habría activado esto en cada corrida de tests.
#
# Render termina TLS en su borde y reenvía la petición a la app por HTTP
# plano, así que request.is_secure() de Django siempre daría False (y
# SECURE_SSL_REDIRECT causaría un loop de redirects) sin decirle a Django
# que confíe en X-Forwarded-Proto -- SECURE_PROXY_SSL_HEADER es justo eso.
# Es seguro confiar en ese header aquí porque Render es el único punto de
# entrada a esta app (no está expuesta en un puerto público aparte que
# alguien pudiera usar para forjar el header directamente).
#
# render.yaml de este proyecto NO define healthCheckPath, así que Render
# solo hace un chequeo TCP de que el puerto esté abierto (nunca un GET real
# a la app) -- si algún día se agrega un healthCheckPath ahí, esa ruta
# necesitaría entrar a SECURE_REDIRECT_EXEMPT para no romper ese chequeo con
# un redirect a HTTPS.
if os.environ.get("RENDER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Conservador a propósito (1h, no el típico 1 año) hasta confirmar en
    # producción real que HTTPS/el dominio están estables -- uno malo con
    # HSTS a un año es mucho más difícil de revertir para los usuarios que
    # ya lo recibieron.
    SECURE_HSTS_SECONDS = 3600
