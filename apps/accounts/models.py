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

    def __str__(self):
        return self.username
