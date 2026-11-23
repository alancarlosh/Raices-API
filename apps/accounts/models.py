from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        APRENDIZ = "aprendiz", "Aprendiz"
        HABLANTE_REVISOR = "hablante_revisor", "Hablante revisor"
        ADMIN = "admin", "Administrador"

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.APRENDIZ,
    )
    # NO CAMBIA el login ni la unicidad del campo `email` -- eso sigue
    # siendo `username`, sin tocar (ver USERNAME_FIELD, intacto). Esto
    # es solo la bandera de "se confirmó que el dueño de la cuenta
    # recibe correo en esa dirección", vía CodigoVerificacionEmail.
    email_verificado = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class CodigoVerificacionEmail(models.Model):
    """Un código de 6 dígitos vigente para confirmar el correo de `usuario`.

    UNA TABLA, Y NO CACHE NI UN CAMPO EN Usuario, a propósito. El
    restablecimiento de contraseña (ver services.py) no necesita guardar
    nada -- default_token_generator deriva el token del propio estado del
    usuario, sin almacenamiento -- pero ESO exige un token largo apto para
    un enlace, no un código corto que alguien pueda escribir a mano. Y el
    cache (LocMemCache en este proyecto, ver REST_FRAMEWORK en
    settings.py) vive por worker: con más de un worker de gunicorn, pedir
    el código en uno y confirmarlo en otro fallaría siempre. Una fila en
    la base no tiene ese problema y sobrevive un reinicio del servicio
    (el que duerme Render tras 15 min, ver config/views.py).

    `solicitar` borra los códigos anteriores del usuario antes de crear
    uno nuevo: solo el último emitido vale, así que pedir otro invalida
    el que no se alcanzó a usar.
    """

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="codigos_verificacion_email"
    )
    codigo = models.CharField(max_length=6)
    creado = models.DateTimeField(auto_now_add=True)
