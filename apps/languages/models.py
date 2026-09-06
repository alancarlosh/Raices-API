from django.db import models


class Lengua(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.SlugField(max_length=20, unique=True, help_text="Código corto, p. ej. 'toto' para totonaco")
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "lengua"
        verbose_name_plural = "lenguas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
