from rest_framework.throttling import ScopedRateThrottle


class RealIpScopedRateThrottle(ScopedRateThrottle):
    """ScopedRateThrottle que identifica al cliente por la IP real, no por
    el valor crudo de X-Forwarded-For.

    DRF's NUM_PROXIES (la forma "estándar" de resolver esto) asume que cada
    proxy AGREGA su propia IP al FINAL de la lista, así que la entrada más
    a la derecha es la más confiable. Render hace lo contrario: siempre
    coloca la IP real del cliente en la PRIMERA posición y solo agrega (sin
    limpiar) lo que el cliente ya haya mandado en ese header — confirmado
    por un ingeniero de Render en su feedback tracker público
    ("we set the first IP in the list to the real client IP") y consistente
    con el artículo oficial "How Render handles DDoS attacks", que indica
    leer x-forwarded-for para obtener la IP real sin mencionar conteo de
    proxies. Por eso NUM_PROXIES no sirve aquí (cuenta desde la derecha,
    que en Render es controlable por quien hace la petición) y hace falta
    leer la PRIMERA entrada explícitamente en su lugar.
    """

    def get_ident(self, request):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class RealIpSostenidoScopedRateThrottle(RealIpScopedRateThrottle):
    """El MISMO límite por IP real, pero en una ventana larga.

    POR QUÉ DOS VENTANAS Y NO UNA MÁS ALTA. Un salón entero entra a la
    vez: 60+ alumnos registrándose desde la MISMA IP pública de la
    escuela en el mismo minuto. Con un solo tope de 10/min, del undécimo
    en adelante recibía 429 — o sea que la prueba de campo se bloqueaba
    sola. Pero subir ese minuto a 90 y dejarlo ahí abriría la puerta a
    129.600 intentos al día desde una sola IP.

    Así que el tope por minuto cubre la RÁFAGA (un grupo entrando junto)
    y este otro, por hora, acota el ABUSO SOSTENIDO, que es un patrón que
    ningún salón produce.

    Lo que NO cambia es `token_obtain_por_cuenta` (5/min): ese es el que
    de verdad frena la fuerza bruta contra una cuenta concreta, sin
    importar desde cuántas IPs venga, y subir los de IP no lo toca.

    Usa su propio `scope_attr` por la misma razón que
    PorCuentaScopedRateThrottle: si leyera `throttle_scope` compartiría
    tasa con el de la ráfaga en vez de limitar lo suyo.
    """

    scope_attr = "throttle_scope_sostenido"


class PorCuentaScopedRateThrottle(ScopedRateThrottle):
    """ScopedRateThrottle que limita por CUENTA objetivo (el `username` del
    body), no por IP.

    RealIpScopedRateThrottle ya limita /api/token/ por IP, pero eso no
    protege una cuenta específica: alguien con muchas IPs distintas (una
    botnet, una VPN rotativa) sigue sin tope real contra un solo username.
    Se usa JUNTO con el throttle de IP en la vista (ver
    TokenObtainPairThrottledView), no en su lugar.

    Preferido sobre instalar `django-axes`: esta app ya resuelve el caso con
    el mismo mecanismo de ventana rodante en caché que el resto del proyecto
    usa para IP (sin modelos/migraciones nuevas, sin backend de auth
    adicional) — suficiente para el volumen de este proyecto. axes sería más
    robusto (cool-off configurable, señales, panel en el admin) pero es una
    dependencia más para un caso que esta clase ya cubre.

    Si el body no trae `username` (o no es JSON parseable), no se aplica
    este throttle en particular — el de IP sigue cubriendo ese caso.

    Usa su propio `scope_attr` (en vez del `throttle_scope` heredado de
    ScopedRateThrottle) para poder convivir con RealIpScopedRateThrottle en
    la misma vista con una tasa distinta — si ambos leyeran `throttle_scope`
    compartirían el mismo scope/tasa en vez de limitar cada uno lo suyo.
    """

    scope_attr = "throttle_scope_por_cuenta"

    def get_cache_key(self, request, view):
        try:
            username = request.data.get("username")
        except Exception:
            username = None

        if not username:
            return None

        return self.cache_format % {"scope": self.scope, "ident": username}
