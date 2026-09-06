from django.conf import settings
from django.db import models

from apps.content.models import ObjetoInteractivo


class ProgresoUsuario(models.Model):
    """Registra que un usuario descubrió un objeto (clic en la exploración)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progresos")
    objeto = models.ForeignKey(ObjetoInteractivo, on_delete=models.CASCADE, related_name="progresos")
    descubierto_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "progreso de usuario"
        verbose_name_plural = "progresos de usuario"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "objeto"], name="unico_progreso_usuario_objeto"),
        ]

    def __str__(self):
        return f"{self.usuario} descubrió {self.objeto}"


class IntentoEscritura(models.Model):
    """Histórico de intentos de escritura; el dominio de una palabra se DERIVA de este historial."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="intentos_escritura")
    objeto = models.ForeignKey(ObjetoInteractivo, on_delete=models.CASCADE, related_name="intentos_escritura")
    texto_ingresado = models.CharField(max_length=150)
    correcto = models.BooleanField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "intento de escritura"
        verbose_name_plural = "intentos de escritura"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.usuario} -> '{self.texto_ingresado}' ({'correcto' if self.correcto else 'incorrecto'})"
