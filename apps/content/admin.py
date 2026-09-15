from django.contrib import admin

from .models import Escena, ObjetoInteractivo


class ObjetoInteractivoInline(admin.TabularInline):
    model = ObjetoInteractivo
    extra = 0
    fields = ("palabra", "glosa_es", "lengua", "estado", "x", "y", "width", "height")


@admin.register(Escena)
class EscenaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "lengua", "orden")
    list_filter = ("lengua",)
    prepopulated_fields = {"codigo": ("nombre",)}
    inlines = [ObjetoInteractivoInline]


@admin.register(ObjetoInteractivo)
class ObjetoInteractivoAdmin(admin.ModelAdmin):
    list_display = ("palabra", "glosa_es", "escena", "lengua", "estado")
    list_filter = ("estado", "lengua", "escena")
    search_fields = ("palabra", "glosa_es")
    actions = ["marcar_publicado", "marcar_en_revision"]

    @admin.action(description="Marcar como publicado")
    def marcar_publicado(self, request, queryset):
        queryset.update(estado=ObjetoInteractivo.Estado.PUBLICADO)

    @admin.action(description="Marcar como en revisión")
    def marcar_en_revision(self, request, queryset):
        queryset.update(estado=ObjetoInteractivo.Estado.EN_REVISION)
