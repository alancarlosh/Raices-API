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
