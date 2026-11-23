from django.urls import path

from .views import (
    ConfirmarResetPasswordView,
    ConfirmarVerificacionEmailView,
    MeView,
    RegistroView,
    SolicitarResetPasswordView,
    SolicitarVerificacionEmailView,
)

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("me/", MeView.as_view(), name="me"),
    path("restablecer-password/", SolicitarResetPasswordView.as_view(), name="restablecer-password"),
    path(
        "restablecer-password/confirmar/",
        ConfirmarResetPasswordView.as_view(),
        name="restablecer-password-confirmar",
    ),
    path("verificar-email/", SolicitarVerificacionEmailView.as_view(), name="verificar-email"),
    path(
        "verificar-email/confirmar/",
        ConfirmarVerificacionEmailView.as_view(),
        name="verificar-email-confirmar",
    ),
]
