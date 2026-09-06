from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from . import selectors
from .serializers import EscenaListSerializer, EscenaSerializer


@method_decorator(cache_page(60 * 15), name="get")
class EscenaListView(ListAPIView):
    """GET /api/escenas/ — listado ligero (id, codigo, nombre, lengua, orden)
    para que el frontend arme su grafo de navegación sin hardcodear ids."""

    permission_classes = [IsAuthenticated]
    serializer_class = EscenaListSerializer

    def get_queryset(self):
        return selectors.escena_list()


@method_decorator(cache_page(60 * 15), name="get")
class EscenaDetailView(RetrieveAPIView):
    """GET /api/escenas/<id>/ — el contenido es casi estático una vez publicado."""

    permission_classes = [IsAuthenticated]
    serializer_class = EscenaSerializer

    def get_object(self):
        return selectors.escena_get_publicada(escena_id=self.kwargs["pk"])
