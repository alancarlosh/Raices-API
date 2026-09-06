import unicodedata

from django.db import models

from apps.languages.models import Lengua


class Escena(models.Model):
    """Un cuarto navegable de la casa virtual."""

    lengua = models.ForeignKey(Lengua, on_delete=models.CASCADE, related_name="escenas")
    nombre = models.CharField(max_length=100)
    fondo = models.URLField(help_text="URL del sprite/imagen de fondo (servido vía CDN)")
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "escena"
        verbose_name_plural = "escenas"
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.nombre} ({self.lengua.codigo})"


class ObjetoInteractivo(models.Model):
    """Un objeto clicable dentro de una escena (silla, mesa, puerta, ...)."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        EN_REVISION = "en_revision", "En revisión"
        PUBLICADO = "publicado", "Publicado"

    escena = models.ForeignKey(Escena, on_delete=models.CASCADE, related_name="objetos")
    lengua = models.ForeignKey(Lengua, on_delete=models.CASCADE, related_name="objetos")
    palabra = models.CharField(max_length=150, help_text="Palabra en la lengua originaria (NFC)")
    sprite = models.URLField(help_text="URL del sprite del objeto (servido vía CDN)")
    audio_ogg = models.URLField(
        help_text="URL del audio en OGG/Opus (formato principal, servido vía CDN)",
    )
    audio_m4a = models.URLField(
        help_text="URL del audio en AAC/M4A (fallback para Safari/iOS, que no soporta Opus en Ogg)",
    )
    x = models.PositiveIntegerField()
    y = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)

    class Meta:
        verbose_name = "objeto interactivo"
        verbose_name_plural = "objetos interactivos"
        ordering = ["id"]

    def save(self, *args, **kwargs):
        # NUNCA usar unidecode ni eliminar diacríticos: el saltillo (Ꞌ) y las
        # vocales largas son fonémicamente distintivos, solo normalizamos forma.
        self.palabra = unicodedata.normalize("NFC", self.palabra)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.palabra} @ {self.escena.nombre}"
