from django.contrib import admin

from .models import MedicionRendimiento


@admin.register(MedicionRendimiento)
class MedicionRendimientoAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "usuario", "escena", "fps_p50", "fps_p5",
                    "fps_min", "dpr", "ajustes", "version", "gpu")
    # `version` y `ajustes` como filtros son LO QUE HACE UTIL LA TABLA:
    # permiten leer "todas las filas del build de ayer" o "todas las que
    # llevan sombras=no" sin exportar nada ni fiarse de la hora.
    list_filter = ("escena", "version", "ajustes", "gpu", "creado_en")
    search_fields = ("usuario__username", "gpu", "navegador", "ajustes", "version")
    # Son MEDIDAS: no se editan. Si una fila está mal, se borra y se vuelve
    # a medir; corregirla a mano produce una tabla que parece datos y no lo
    # es, que es el peor resultado posible para un capítulo de resultados.
    readonly_fields = [f.name for f in MedicionRendimiento._meta.fields]

    def has_add_permission(self, request):
        return False
