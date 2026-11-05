"""Decide qué backend de correo usar de verdad, a partir de lo configurado.

Existe por un estado intermedio que es PEOR que no configurar nada: encender
`EMAIL_BACKEND` en SMTP sin que estén las credenciales. En ese estado
`send_mail` revienta, y como `apps/accounts/services.py` lo llama con
`fail_silently=False` y la vista no atrapa nada, "recuperar contraseña"
pasaría de responder 200 (con el enlace escrito en el log del servidor:
invisible, pero limpio) a devolver un 500 en la cara del usuario.

La degradación segura es volver al backend de consola y DECIRLO: la
aplicación sigue en pie, el endpoint sigue respondiendo su 200 genérico, y
quien lea el log se encuentra con qué falta. Nunca se eleva una excepción
aquí a propósito: una configuración de correo incompleta no debería tumbar
escenas, login ni progreso, que no tienen nada que ver con el correo.

El render.yaml de este proyecto ya evita el estado intermedio de otra forma
(declara EMAIL_BACKEND como sync:false, así que el interruptor y las
credenciales se encienden juntos). Esto protege el otro caso: cualquiera
--incluido Alan escribiendo variables a mano en el panel-- encendiendo el
interruptor sin lo demás.
"""

SMTP = "django.core.mail.backends.smtp.EmailBackend"
CONSOLE = "django.core.mail.backends.console.EmailBackend"

# El remitente por defecto de settings.py. No es una dirección real ni está
# verificada en Brevo, y el relay rechaza un remitente no verificado, así que
# dejarla puesta con SMTP encendido es tan incompleto como no tener clave.
REMITENTE_PLACEHOLDER = "no-responder@raices.local"


def resolver(*, backend: str, host_user: str, host_password: str, from_email: str) -> tuple[str, list[str]]:
    """Devuelve (backend a usar, lista de lo que falta para poder enviar).

    Si no se pidió SMTP, no opina: devuelve el backend tal cual y nada que
    falte. Así `console`, `locmem` (que usan las pruebas) o cualquier otro
    pasan sin tocarse.
    """
    if backend != SMTP:
        return backend, []

    falta = []
    if not host_user:
        falta.append("EMAIL_HOST_USER")
    if not host_password:
        falta.append("EMAIL_HOST_PASSWORD")
    if not from_email or from_email == REMITENTE_PLACEHOLDER:
        falta.append("DEFAULT_FROM_EMAIL (sigue en el placeholder local; Brevo rechaza un remitente no verificado)")

    return (CONSOLE if falta else SMTP), falta
