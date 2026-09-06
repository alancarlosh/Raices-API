from django.urls import path

from .views import ObjetoDescubrirView, ObjetoIntentoEscrituraView, ProgresoResumenView

urlpatterns = [
    path("objetos/<int:pk>/descubrir/", ObjetoDescubrirView.as_view(), name="objeto-descubrir"),
    path("objetos/<int:pk>/intento-escritura/", ObjetoIntentoEscrituraView.as_view(), name="objeto-intento-escritura"),
    path("progreso/", ProgresoResumenView.as_view(), name="progreso-resumen"),
]
