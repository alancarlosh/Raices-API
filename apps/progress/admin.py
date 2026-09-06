from django.contrib import admin

from .models import IntentoEscritura, ProgresoUsuario


@admin.register(ProgresoUsuario)
class ProgresoUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "objeto", "descubierto_en")
    list_filter = ("objeto__escena",)


@admin.register(IntentoEscritura)
class IntentoEscrituraAdmin(admin.ModelAdmin):
    list_display = ("usuario", "objeto", "texto_ingresado", "correcto", "creado_en")
    list_filter = ("correcto", "objeto__escena")
