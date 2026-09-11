from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .serializers import RegistroSerializer, UsuarioSerializer


class TokenObtainPairThrottledView(TokenObtainPairView):
    """POST /api/token/ con rate limiting — la API ya está en una URL pública,
    sin límite cualquiera puede intentar fuerza bruta contra contraseñas."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_obtain"


class RegistroView(APIView):
    """POST /api/registro/ — registro mínimo viable: username/email/password.

    Devuelve el mismo par access/refresh que POST /api/token/ para que el
    frontend pueda dejar al usuario autenticado de una vez, sin una segunda
    llamada a /api/token/ inmediatamente después de registrarse.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
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
