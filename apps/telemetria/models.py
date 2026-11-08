from django.conf import settings
from django.db import models


class MedicionRendimiento(models.Model):
    """Cuántos cuadros por segundo le dio el recorrido 3D a UNA máquina.

    POR QUÉ EXISTE. El recorrido caminable se entrega a un salón de clase
    entero, y hasta ahora el único dato de rendimiento del proyecto es el
    del portátil del autor. Eso no sirve ni para decidir qué optimizar ni
    para escribirlo en la tesis: un equipo de laboratorio escolar y un
    MacBook Air no se parecen en nada, y la escena exterior ya es el caso
    caro (20 MB de geometría, ~2.000 mallas).

    QUÉ SE GUARDA Y QUÉ NO. Se guarda el resumen de UNA sesión en UNA
    escena, no una serie temporal: tres cifras de cuadros, el tamaño real
    que se está dibujando y con qué hardware. Es deliberado que no haya
    muestreo continuo — multiplica el volumen, no cambia la conclusión
    ("este equipo sufre en el exterior") y mete al proyecto en un terreno
    de datos personales que no quiere pisar con alumnos.

    NO LLEVA IDENTIFICADOR DE MÁQUINA, a propósito. Cada alumno entra con
    su propia cuenta (decisión de Alan, 2026-11-07), así que el usuario ya
    separa los equipos y no hace falta huella del navegador. Si algún día
    se usara una cuenta compartida habría que añadir un identificador
    anónimo, porque entonces las filas de treinta alumnos quedarían
    mezcladas y la tabla dejaría de responder a la pregunta.

    LAS TRES CIFRAS DE CUADROS SON MEDIANA, PERCENTIL 5 Y MÍNIMO, y el
    promedio NO está entre ellas por la misma razón que explica
    RoomWalk.tsx: lo que se siente como "va mal" son los tirones, y un
    promedio los esconde. El p5 es el peor segundo de cada veinte.

    `muestras` son SEGUNDOS CONTADOS, no segundos transcurridos: el cliente
    solo acumula los segundos en que el personaje de verdad se movió medio
    metro, y tira los primeros cinco mientras cargan los .glb y se compilan
    los sombreadores. Una medida con pocas muestras es ruido; por eso el
    serializador exige un mínimo.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="mediciones_rendimiento",
    )
    escena = models.CharField(max_length=32)

    fps_p50 = models.PositiveSmallIntegerField("cuadros/s medianos")
    fps_p5 = models.PositiveSmallIntegerField("cuadros/s percentil 5")
    fps_min = models.PositiveSmallIntegerField("cuadros/s mínimos")
    muestras = models.PositiveSmallIntegerField("segundos contados")

    # El dpr EFECTIVO al terminar de medir, que puede no ser el inicial: la
    # escalera adaptativa baja de 1.25 a 1.0 y a 0.8 cuando los cuadros caen
    # por debajo de 28. Guardarlo es lo que permite distinguir "va a 45
    # cuadros" de "va a 45 cuadros PORQUE ya bajó dos escalones de
    # resolución", que son dos máquinas muy distintas.
    dpr = models.FloatField("densidad de píxeles efectiva")
    pixeles = models.PositiveIntegerField("píxeles dibujados por cuadro")
    mallas = models.PositiveIntegerField()

    # Texto tal cual lo reporta el navegador. Puede venir vacío: Firefox y
    # los navegadores con resistencia a huella digital no exponen
    # WEBGL_debug_renderer_info, y entonces no hay forma de saber la GPU.
    # Que falte es un dato en sí mismo, no un error.
    gpu = models.CharField(max_length=120, blank=True)
    navegador = models.CharField(max_length=200, blank=True)
    nucleos = models.PositiveSmallIntegerField(null=True, blank=True)
    memoria_gb = models.FloatField(null=True, blank=True)

    # CON QUÉ AJUSTES SE MIDIÓ, en formato `clave=valor;clave=valor`
    # (p. ej. `sombras=no;dpr=fijo`).
    #
    # POR QUÉ SE AÑADIÓ (2026-11-08). La tabla guardaba el dpr efectivo
    # pero no si las sombras estaban encendidas, así que dos mediciones
    # tomadas A PROPÓSITO con ajustes distintos — que es justo lo que se
    # hace para decidir qué optimizar — llegaban aquí con el mismo
    # aspecto. Compararlas habría sido inventar. Texto libre y no un
    # conjunto de columnas porque los mandos van a cambiar durante la
    # sesión de rendimiento y no quiero una migración por cada uno.
    ajustes = models.CharField(max_length=120, blank=True)

    # SHA corto del bundle que tomó la medida, inyectado al compilar.
    #
    # Es lo que separa el "antes" del "después" de un despliegue. La hora
    # de creación NO sirve para eso: un alumno puede tener abierta desde
    # ayer una pestaña con el bundle viejo y mandar una fila hoy.
    # Puede venir vacío (`sin-git`, o filas anteriores a este campo).
    version = models.CharField(max_length=40, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "medición de rendimiento"
        verbose_name_plural = "mediciones de rendimiento"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["escena", "-creado_en"]),
            models.Index(fields=["usuario", "escena"]),
        ]

    def __str__(self):
        return f"{self.usuario} en {self.escena}: p50 {self.fps_p50} (dpr {self.dpr})"
