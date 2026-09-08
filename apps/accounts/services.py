from .models import Usuario


def usuario_registrar(*, username: str, password: str, email: str = "") -> Usuario:
    """Crea un usuario real con rol 'aprendiz' por defecto.

    El rol nunca se acepta como input de registro: asignar hablante_revisor o
    admin es una acción deliberada desde el admin de Django, no algo que un
    usuario pueda auto-otorgarse al registrarse.
    """
    return Usuario.objects.create_user(username=username, email=email, password=password)
