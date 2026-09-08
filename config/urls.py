from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as servir_media
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.content.urls")),
    path("api/", include("apps.progress.urls")),
]

# Sirve MEDIA_ROOT localmente (audio placeholder/ingerido de desarrollo).
# django.conf.urls.static.static() no sirve aquí: internamente no-opea si
# settings.DEBUG es False, y pytest-django fuerza DEBUG=False antes de que se
# resuelva el urlconf, así que la ruta nunca quedaría registrada para los
# tests. Registrar la vista a mano evita ese no-op. Es inofensivo en
# producción: ahí audio_ogg/audio_m4a apuntan a un CDN real (ver README),
# nunca a /media/.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", servir_media, {"document_root": settings.MEDIA_ROOT}),
]
