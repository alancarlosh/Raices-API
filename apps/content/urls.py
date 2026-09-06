from django.urls import path

from .views import EscenaDetailView

urlpatterns = [
    path("escenas/<int:pk>/", EscenaDetailView.as_view(), name="escena-detail"),
]
