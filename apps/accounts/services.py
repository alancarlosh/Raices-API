import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Usuario

# Cuanto vive un codigo de verificacion antes de que confirmar() lo
# rechace por caducado. 15 minutos: suficiente para ir al correo y
# volver sin apurarse, y corto para que una fuerza bruta contra 1.000.000
# de combinaciones (ver verificar_email_confirmar en settings.py) tenga
# que reiniciarse constantemente contra un codigo nuevo.
DURACION_CODIGO_VERIFICACION = timedelta(minutes=15)


def usuario_registrar(*, username: str, email: str, password: str) -> Usuario:
    """Crea un usuario real con rol 'aprendiz' por defecto.

    El rol nunca se acepta como input de registro: asignar hablante_revisor o
    admin es una acción deliberada desde el admin de Django, no algo que un
    usuario pueda auto-otorgarse al registrarse.
    """
    return Usuario.objects.create_user(username=username, email=email, password=password)


def password_reset_solicitar(*, email: str) -> None:
    """Envía un correo con enlace para restablecer la contraseña, si existe
    una cuenta con ese email. Nunca distingue el caso "no existe" hacia quien
    llama (ver SolicitarResetPasswordView) — evita que alguien use este
    endpoint para averiguar qué correos están registrados.

    EMAIL_BACKEND es 'console' por defecto (ver settings.py) hasta que
    existan credenciales de Brevo (el proveedor elegido) como variables de
    entorno en Render — mientras tanto el correo se ve en los logs del
    servidor, no llega de verdad a la bandeja del usuario. Ver
    config/email_backend.py para la guarda que evita el estado a medio
    configurar.

    Ya NO es el único send_mail del proyecto: verificacion_email_solicitar
    (abajo) manda el código de verificación. Las dos comparten el mismo
    scope de throttle sostenido porque gastan el mismo cupo de Brevo — ver
    envio_correo_sostenido en settings.py.
    """
    usuario = Usuario.objects.filter(email=email).first()
    if usuario is None:
        return

    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    enlace = f"{settings.FRONTEND_URL}/restablecer-password?uid={uid}&token={token}"

    send_mail(
        subject="Restablece tu contraseña en Raíces",
        message=(
            "Alguien (con suerte tú) solicitó restablecer la contraseña de tu cuenta en Raíces.\n\n"
            f"Usa este enlace para elegir una nueva contraseña:\n{enlace}\n\n"
            "Si tú no lo solicitaste, puedes ignorar este correo."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def password_reset_confirmar(*, usuario: Usuario, password: str) -> Usuario:
    usuario.set_password(password)
    usuario.save()
    return usuario


def verificacion_email_solicitar(*, usuario: Usuario) -> None:
    """Genera un código de 6 dígitos y lo manda al correo de `usuario`.

    Borra los códigos anteriores del usuario antes de crear el nuevo: solo
    el último emitido vale (ver CodigoVerificacionEmail). `secrets` y no
    `random` -- es un código de seguridad, tiene que venir de un
    generador criptográfico, no del PRNG de propósito general.
    """
    usuario.codigos_verificacion_email.all().delete()
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.codigos_verificacion_email.create(codigo=codigo)

    send_mail(
        subject="Tu código para verificar tu correo en Raíces",
        message=(
            f"Tu código de verificación es: {codigo}\n\n"
            "Escríbelo en Raíces para confirmar que esta cuenta es tuya. "
            "Caduca en 15 minutos.\n\n"
            "Si tú no lo solicitaste, puedes ignorar este correo."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )


def verificacion_email_confirmar(*, usuario: Usuario, codigo: str) -> bool:
    """True y marca el correo como verificado si `codigo` es el último
    código vigente de `usuario`; False en cualquier otro caso (no existe,
    no es el último, o caducó) -- un código equivocado es una respuesta
    de negocio para quien llama (ver ConfirmarVerificacionEmailView), no
    una excepción.

    Un código acertado se consume: se borran TODOS los códigos del
    usuario, no solo el que coincidió, así que un código vigente no se
    puede reutilizar una vez que uno ya sirvió.
    """
    desde = timezone.now() - DURACION_CODIGO_VERIFICACION
    coincide = usuario.codigos_verificacion_email.filter(codigo=codigo, creado__gte=desde).exists()
    if coincide:
        usuario.codigos_verificacion_email.all().delete()
        usuario.email_verificado = True
        usuario.save(update_fields=["email_verificado"])
    return coincide
