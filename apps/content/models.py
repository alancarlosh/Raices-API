import unicodedata

from django.db import models

from apps.languages.models import Lengua


class Escena(models.Model):
    """Un cuarto navegable de la casa virtual."""

    lengua = models.ForeignKey(Lengua, on_delete=models.CASCADE, related_name="escenas")
    codigo = models.SlugField(
        max_length=50, unique=True, help_text="Identificador estable para el frontend, ej. 'cocina'"
    )
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
        # Estuvo publicado y salió del temario (p. ej. la poda del Baño de
        # octubre 2026, ver apps/content/seed_data.py). No es BORRADOR: eso
        # significa "todavía no está listo", y confundiría a un
        # hablante-revisor en el admin. Existe para que `seed_demo` pueda
        # sacar una palabra del recorrido SIN borrar su fila, porque
        # ProgresoUsuario e IntentoEscritura apuntan aquí con CASCADE y
        # borrar la fila se lleva el progreso real de los usuarios.
        RETIRADO = "retirado", "Retirado"

    escena = models.ForeignKey(Escena, on_delete=models.CASCADE, related_name="objetos")
    lengua = models.ForeignKey(Lengua, on_delete=models.CASCADE, related_name="objetos")
    palabra = models.CharField(
        max_length=150,
        help_text="Palabra REAL en la lengua originaria (NFC), validada por el asesor/hablantes "
        "nativos. Es lo que se compara contra la escritura del usuario en "
        "apps/progress/services.py. Mientras ese vocabulario no llegue, sigue conteniendo "
        "el mismo placeholder en español que glosa_es (ver seed_data.py).",
    )
    glosa_es = models.CharField(
        max_length=150,
        default="",
        blank=True,
        help_text="Glosa/etiqueta en español para mostrar en la UI (ej. junto al audio). "
        "Independiente de `palabra`: no se usa para validar la escritura del usuario.",
    )
    sprite_key = models.CharField(
        max_length=100,
        help_text="Clave del frame en el texture atlas del frontend (ej. 'chair_wood_a'); "
        "el sprite en sí vive empacado en Raices-Front, no se sirve desde el backend",
    )
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
        self.glosa_es = unicodedata.normalize("NFC", self.glosa_es)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.palabra} @ {self.escena.nombre}"
