from django.urls import path

from .views import MedicionRendimientoCrearView, ResumenRendimientoView

urlpatterns = [
    path("rendimiento/", MedicionRendimientoCrearView.as_view(), name="rendimiento-crear"),
    path("rendimiento/resumen/", ResumenRendimientoView.as_view(), name="rendimiento-resumen"),
]
