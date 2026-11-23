from django.contrib.auth.backends import ModelBackend

from .models import Usuario


class EmailBackend(ModelBackend):
    """Autentica por `email` en vez de `username`.

    USERNAME_FIELD de Usuario sigue siendo "username" -- no se toca, y con
    razon: cambiarlo afecta al admin de Django, a `createsuperuser` y a
    cualquier lookup que dependa de el. Este backend es la unica pieza que
    de verdad necesita hablar de correos, y solo la usa
    EmailTokenObtainPairSerializer (ver serializers.py) a traves de
    AUTHENTICATION_BACKENDS (settings.py) -- el ModelBackend normal sigue
    ahi, en la misma lista, para que el admin y `createsuperuser` sigan
    pidiendo username sin que nada se rompa.

    MISMO COSTO DE HASH EXISTA O NO LA CUENTA. Sin el `set_password` de
    abajo, "no existe esa cuenta" respondería más rápido que "existe pero
    la contraseña está mal" -- una diferencia de tiempo que ya es una
    fuga de información (confirma qué correos tienen cuenta). Es el mismo
    patrón que ya usa ModelBackend para `username` inexistente.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        try:
            # iexact: un correo no debería depender de mayúsculas/minúsculas.
            usuario = Usuario._default_manager.get(email__iexact=email)
        except (Usuario.DoesNotExist, Usuario.MultipleObjectsReturned):
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
