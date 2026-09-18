from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Usuario


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

    EMAIL_BACKEND es 'console' por defecto (ver settings.py) mientras no se
    decida un servicio de envío real para producción — el correo se ve en
    los logs del servidor, no llega de verdad a la bandeja del usuario.
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
