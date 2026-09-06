from django.urls import path

from .views import EscenaDetailView, EscenaListView

urlpatterns = [
    path("escenas/", EscenaListView.as_view(), name="escena-list"),
    path("escenas/<int:pk>/", EscenaDetailView.as_view(), name="escena-detail"),
]
