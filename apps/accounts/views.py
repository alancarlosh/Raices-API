from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .serializers import (
    ConfirmarResetPasswordSerializer,
    RegistroSerializer,
    SolicitarResetPasswordSerializer,
    UsuarioSerializer,
)
from .throttling import PorCuentaScopedRateThrottle, RealIpScopedRateThrottle


class MeView(APIView):
    """GET /api/me/ — datos del usuario autenticado (username/email/rol).

    Evita que el frontend dependa de lo que capturó en el momento del
    login/registro, que puede desincronizarse entre dispositivos/sesiones o
    si esos datos cambian del lado del servidor.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class TokenObtainPairThrottledView(TokenObtainPairView):
    """POST /api/token/ con rate limiting — la API ya está en una URL pública,
    sin límite cualquiera puede intentar fuerza bruta contra contraseñas.

    Dos throttles independientes: por IP (RealIpScopedRateThrottle) Y por la
    cuenta objetivo (PorCuentaScopedRateThrottle) — sin el segundo, un
    atacante con muchas IPs distintas podría seguir intentando fuerza bruta
    contra un solo username sin tope real.
    """

    throttle_classes = [RealIpScopedRateThrottle, PorCuentaScopedRateThrottle]
    throttle_scope = "token_obtain"
    throttle_scope_por_cuenta = "token_obtain_por_cuenta"


class RegistroView(APIView):
    """POST /api/registro/ — registro mínimo viable: username/email/password.

    Devuelve el mismo par access/refresh que POST /api/token/ para que el
    frontend pueda dejar al usuario autenticado de una vez, sin una segunda
    llamada a /api/token/ inmediatamente después de registrarse.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RealIpScopedRateThrottle]
    throttle_scope = "registro"

    def post(self, request):
        entrada = RegistroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        usuario = services.usuario_registrar(**entrada.validated_data)

        refresh = RefreshToken.for_user(usuario)
        return Response(
            {
                "user": UsuarioSerializer(usuario).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=201,
        )


class SolicitarResetPasswordView(APIView):
    """POST /api/restablecer-password/ — solicita el enlace para restablecer
    la contraseña de la cuenta con el email dado.

    Siempre responde 200 con el mismo mensaje genérico exista o no una cuenta
    con ese correo, para no dejar que este endpoint se use para averiguar qué
    correos están registrados (user enumeration).
    """

    permission_classes = [AllowAny]
    throttle_classes = [RealIpScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        entrada = SolicitarResetPasswordSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        services.password_reset_solicitar(email=entrada.validated_data["email"])

        return Response(
            {"detail": "Si existe una cuenta con ese correo, se envió un enlace para restablecer la contraseña."}
        )


class ConfirmarResetPasswordView(APIView):
    """POST /api/restablecer-password/confirmar/ — aplica la nueva
    contraseña dado el uid/token del enlace enviado por
    SolicitarResetPasswordView."""

    permission_classes = [AllowAny]
    throttle_classes = [RealIpScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        entrada = ConfirmarResetPasswordSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        services.password_reset_confirmar(
            usuario=entrada.validated_data["usuario"],
            password=entrada.validated_data["password"],
        )

        return Response({"detail": "Contraseña actualizada correctamente."})
