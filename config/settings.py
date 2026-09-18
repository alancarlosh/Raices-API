"""
Django settings for the Raíces project.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-in-production")

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
    "DEFAULT_THROTTLE_RATES": {
        "registro": "10/min",
        "token_obtain": "10/min",
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
