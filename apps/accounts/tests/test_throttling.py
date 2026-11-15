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


# --- EL COSTE DE HASHEAR ------------------------------------------------
#
# Vive en este archivo porque es el mismo tema: lo que decide si un salon
# entero puede entrar a la vez. El throttle era el tope declarado; esto es
# el tope real.

def test_el_hasheador_no_baja_del_minimo_recomendado():
    """600.000 iteraciones es el suelo, no una sugerencia.

    Se bajo de 1.000.000 porque en el plan gratuito de Render cada login
    costaba ~1,8 s de CPU y la prueba de campo son grupos de 60+ alumnos
    registrandose a la vez (ver apps/accounts/hashers.py). Pero 600.000 es
    el minimo que OWASP recomienda para PBKDF2-HMAC-SHA256: por debajo de
    ahi ya no es un ajuste de rendimiento sino una rebaja de seguridad.

    Esta prueba existe para que ese siguiente paso -- "y si lo bajamos un
    poco mas, que la prueba va lenta" -- falle aqui y se tenga que
    discutir, en vez de colarse en un commit de rendimiento.
    """
    from django.contrib.auth.hashers import get_hasher

    from apps.accounts.hashers import PBKDF2SeiscientosMil

    hasheador = get_hasher("default")
    assert hasheador.algorithm == "pbkdf2_sha256"
    assert hasheador.iterations >= 600_000
    # Y QUE SEA EL NUESTRO, que es la otra mitad. Con solo la linea de
    # arriba, el hasheador de Django (1.000.000) tambien pasaba, asi que
    # la prueba no habria notado que PASSWORD_HASHERS desapareciera de la
    # configuracion: volveriamos a los ~1,8 s por login y al salon
    # atascado, en silencio y con todo en verde.
    assert isinstance(hasheador, PBKDF2SeiscientosMil)


def test_las_contrasenas_viejas_se_siguen_verificando():
    """El numero de iteraciones va DENTRO del hash, asi que bajar el de la
    clase no invalida lo ya guardado.

    Es la pregunta que hay que contestar antes de tocar un hasheador en
    produccion: si esto fallara, el cambio dejaria fuera a todas las
    cuentas existentes -- y se descubriria con los alumnos delante.
    """
    from django.contrib.auth.hashers import PBKDF2PasswordHasher, check_password

    viejo = PBKDF2PasswordHasher()
    guardado = viejo.encode("ContraseñaSegura123", viejo.salt())
    assert f"${viejo.iterations}$" in guardado

    assert check_password("ContraseñaSegura123", guardado)
    assert not check_password("otra-cosa", guardado)
