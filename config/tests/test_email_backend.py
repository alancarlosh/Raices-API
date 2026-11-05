"""Pruebas de la guarda del backend de correo.

El caso que importa no es el feliz: es el intermedio. Con SMTP encendido y
credenciales a medias, `send_mail` revienta y "recuperar contraseña"
devuelve 500 al usuario, porque services.py llama con fail_silently=False y
la vista no atrapa nada. Estas pruebas fijan que ese estado degrade a
consola en vez de reventar.
"""

from config.email_backend import CONSOLE, REMITENTE_PLACEHOLDER, SMTP, resolver

CREDENCIALES_OK = {
    "host_user": "8xxxxx@smtp-brevo.com",
    "host_password": "clave-smtp",
    "from_email": "raices@ejemplo.org",
}


def test_smtp_completo_se_queda_en_smtp():
    backend, falta = resolver(backend=SMTP, **CREDENCIALES_OK)

    assert backend == SMTP
    assert falta == []


def test_sin_usuario_degrada_a_consola():
    backend, falta = resolver(backend=SMTP, **{**CREDENCIALES_OK, "host_user": ""})

    assert backend == CONSOLE
    assert falta == ["EMAIL_HOST_USER"]


def test_sin_clave_degrada_a_consola():
    backend, falta = resolver(backend=SMTP, **{**CREDENCIALES_OK, "host_password": ""})

    assert backend == CONSOLE
    assert falta == ["EMAIL_HOST_PASSWORD"]


def test_remitente_placeholder_degrada_a_consola():
    """Brevo rechaza un remitente no verificado, así que dejar el placeholder
    local con SMTP encendido es tan incompleto como no tener clave."""
    backend, falta = resolver(backend=SMTP, **{**CREDENCIALES_OK, "from_email": REMITENTE_PLACEHOLDER})

    assert backend == CONSOLE
    assert falta and falta[0].startswith("DEFAULT_FROM_EMAIL")


def test_enumera_todo_lo_que_falta_de_una_vez():
    """Quien lea el aviso debería poder arreglarlo en un viaje, no
    descubriendo una variable por despliegue."""
    backend, falta = resolver(backend=SMTP, host_user="", host_password="", from_email="")

    assert backend == CONSOLE
    assert len(falta) == 3


def test_no_opina_si_no_se_pidio_smtp():
    """console y locmem (el de las pruebas) tienen que pasar sin tocarse,
    incluso sin ninguna credencial."""
    for otro in (CONSOLE, "django.core.mail.backends.locmem.EmailBackend"):
        backend, falta = resolver(backend=otro, host_user="", host_password="", from_email="")
        assert backend == otro
        assert falta == []
