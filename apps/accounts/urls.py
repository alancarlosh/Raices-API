from django.urls import path

from .views import MeView, RegistroView

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("me/", MeView.as_view(), name="me"),
]
