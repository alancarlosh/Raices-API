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
