from django.urls import path

from .views import ConfirmarResetPasswordView, MeView, RegistroView, SolicitarResetPasswordView

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("me/", MeView.as_view(), name="me"),
    path("restablecer-password/", SolicitarResetPasswordView.as_view(), name="restablecer-password"),
    path(
        "restablecer-password/confirmar/",
        ConfirmarResetPasswordView.as_view(),
        name="restablecer-password-confirmar",
    ),
]
