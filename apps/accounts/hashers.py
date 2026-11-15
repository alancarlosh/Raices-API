from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PBKDF2SeiscientosMil(PBKDF2PasswordHasher):
    """PBKDF2-SHA256 con 600.000 iteraciones en vez del millón de Django 5.2.

    POR QUÉ SE BAJA, Y ESTÁ MEDIDO EN LA MÁQUINA QUE IMPORTA. En el plan
    gratuito de Render un login tarda **1,96 s**, y el reparto es claro:

        404 (sin hash, sin base de datos)   0,15 s
        lectura de base de datos            0,14 s
        login                               1,96 s

    O sea que ~1,8 s de cada login son CPU hasheando — no red, no base de
    datos. Esa CPU es unas diez veces más lenta que un portátil: el mismo
    millón de iteraciones son 183 ms en la máquina de desarrollo.

    Y el servicio arranca con `gunicorn config.wsgi:application` sin
    `--workers`, cuyo defecto es UN worker sync: una petición a la vez. Así
    que el techo real eran ~33 registros por minuto, muy por debajo de los
    90/min que el throttle permite. La prueba de campo son varios grupos de
    60+ alumnos registrándose a la vez, y a 2 s por alumno el último
    esperaba unos DOS MINUTOS.

    POR QUÉ 600.000 Y NO MENOS. Es el mínimo que OWASP recomienda hoy para
    PBKDF2-HMAC-SHA256, así que esto no baja la guardia por debajo de la
    recomendación vigente: la deja justo en ella. Medido, el recorte es
    lineal como cabe esperar (183 -> 109 ms en desarrollo, 0,598x), así que
    en Render queda en ~1,08 s y el techo sube a ~55 por minuto.

    Más workers no era la salida: el trabajo es CPU y el plan gratuito da
    una fracción de núcleo, así que dos workers se pelearían por la misma.

    SOBRE LAS CONTRASEÑAS QUE YA EXISTEN: el número de iteraciones va
    DENTRO del hash guardado, así que las antiguas se siguen verificando
    sin tocar nada. Django las vuelve a hashear al siguiente acceso bueno
    (`must_update` compara las iteraciones guardadas con las de esta
    clase), o sea que ese primer login todavía paga el millón y los
    siguientes ya no. Las cuentas nuevas se benefician desde la primera.
    """

    iterations = 600_000
