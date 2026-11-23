from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .serializers import (
    ConfirmarResetPasswordSerializer,
    ConfirmarVerificacionEmailSerializer,
    RegistroSerializer,
    SolicitarResetPasswordSerializer,
    UsuarioSerializer,
)
from .throttling import (
    PorCuentaScopedRateThrottle,
    RealIpScopedRateThrottle,
    RealIpSostenidoScopedRateThrottle,
)


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

    throttle_classes = [
        RealIpScopedRateThrottle,
        RealIpSostenidoScopedRateThrottle,
        PorCuentaScopedRateThrottle,
    ]
    throttle_scope = "token_obtain"
    throttle_scope_sostenido = "token_obtain_sostenido"
    throttle_scope_por_cuenta = "token_obtain_por_cuenta"


class RegistroView(APIView):
    """POST /api/registro/ — registro mínimo viable: username/email/password.

    Devuelve el mismo par access/refresh que POST /api/token/ para que el
    frontend pueda dejar al usuario autenticado de una vez, sin una segunda
    llamada a /api/token/ inmediatamente después de registrarse.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RealIpScopedRateThrottle, RealIpSostenidoScopedRateThrottle]
    throttle_scope = "registro"
    throttle_scope_sostenido = "registro_sostenido"

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
    # CON SOSTENIDO, Y SOLO AQUI -- ConfirmarResetPasswordView (abajo) no
    # lo lleva porque no envia correo: comparte scope "password_reset"
    # para el tope de rafaga, pero el sostenido protege especificamente
    # el cupo de Brevo, y confirmar no lo gasta. Ver DEFAULT_THROTTLE_
    # RATES en settings.py para la cuenta completa.
    #
    # "envio_correo_sostenido" Y NO "password_reset_sostenido": este
    # scope lo comparte tambien SolicitarVerificacionEmailView, porque
    # las dos gastan el MISMO cupo de Brevo -- ver el comentario largo en
    # settings.py sobre por que no llevan cada una el suyo.
    throttle_classes = [RealIpScopedRateThrottle, RealIpSostenidoScopedRateThrottle]
    throttle_scope = "password_reset"
    throttle_scope_sostenido = "envio_correo_sostenido"

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


class SolicitarVerificacionEmailView(APIView):
    """POST /api/verificar-email/ — manda un código de 6 dígitos al correo
    de la cuenta AUTENTICADA, para confirmar que de verdad es suya.

    AUTENTICADO, Y ESA ES LA DIFERENCIA DE FONDO CON EL RESTABLECIMIENTO
    DE CONTRASEÑA. SolicitarResetPasswordView es AllowAny porque quien lo
    llama puede no tener sesión todavía, y por eso tiene que responder
    igual exista o no la cuenta (anti-enumeración). Aquí no hace falta
    nada de eso: IsAuthenticated ya prueba que quien pide el código es
    dueño de la cuenta, con su propio access token. Un tercero no puede
    pedir el código de otra persona aunque sepa su correo.
    """

    permission_classes = [IsAuthenticated]
    # Mismo scope sostenido que SolicitarResetPasswordView, a proposito
    # -- ver el comentario de esa vista y el de settings.py.
    throttle_classes = [RealIpScopedRateThrottle, RealIpSostenidoScopedRateThrottle]
    throttle_scope = "verificar_email"
    throttle_scope_sostenido = "envio_correo_sostenido"

    def post(self, request):
        if request.user.email_verificado:
            # No es un error -- es el estado que se pedía lograr. Pedirlo
            # de nuevo no debe gastar un correo ni confundir con un 400.
            return Response({"detail": "Tu correo ya está verificado."})

        services.verificacion_email_solicitar(usuario=request.user)
        return Response({"detail": "Te enviamos un código a tu correo."})


class ConfirmarVerificacionEmailView(APIView):
    """POST /api/verificar-email/confirmar/ — valida el código de 6
    dígitos contra la cuenta autenticada y marca su correo como
    verificado."""

    permission_classes = [IsAuthenticated]
    # Tope de FUERZA BRUTA contra el codigo, no de cupo de correo: esta
    # vista no envia nada. Scope propio y sin sostenido -- ver
    # DEFAULT_THROTTLE_RATES en settings.py.
    throttle_classes = [RealIpScopedRateThrottle]
    throttle_scope = "verificar_email_confirmar"

    def post(self, request):
        entrada = ConfirmarVerificacionEmailSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        verificado = services.verificacion_email_confirmar(
            usuario=request.user, codigo=entrada.validated_data["codigo"]
        )
        if not verificado:
            # 400 y no 404/422: es un dato de entrada incorrecto (el
            # codigo), el mismo tratamiento que un password invalido en
            # el serializer de arriba -- no se distingue "no existe tal
            # codigo" de "ya caduco" para no regalarle a quien adivina
            # informacion sobre CUAL de los dos paso.
            return Response({"detail": "Código incorrecto o caducado."}, status=400)

        return Response({"detail": "Correo verificado correctamente."})
