from rest_framework.test import APIRequestFactory

from apps.accounts.throttling import RealIpScopedRateThrottle


def test_get_ident_usa_la_primera_entrada_de_x_forwarded_for():
    # Render siempre pone la IP real del cliente primero y solo agrega
    # (nunca limpia) lo que el cliente ya haya mandado — así que la entrada
    # de la derecha puede ser controlada por quien hace la petición.
    request = APIRequestFactory().post("/", HTTP_X_FORWARDED_FOR="203.0.113.9, 1.2.3.4")

    assert RealIpScopedRateThrottle().get_ident(request) == "203.0.113.9"


def test_get_ident_ignora_valores_inventados_despues_de_la_ip_real():
    throttle = RealIpScopedRateThrottle()
    base = APIRequestFactory().post("/", HTTP_X_FORWARDED_FOR="203.0.113.9")
    variante = APIRequestFactory().post(
        "/", HTTP_X_FORWARDED_FOR="203.0.113.9, valor-que-alguien-se-inventó"
    )

    # Mismo cliente real (misma primera IP) debe identificarse igual sin
    # importar qué basura agregue después en el header — de lo contrario
    # alguien podría variar esa cola para esquivar el throttling.
    assert throttle.get_ident(base) == throttle.get_ident(variante)


def test_get_ident_cae_a_remote_addr_sin_x_forwarded_for():
    request = APIRequestFactory().post("/")
    request.META["REMOTE_ADDR"] = "127.0.0.1"

    assert RealIpScopedRateThrottle().get_ident(request) == "127.0.0.1"
