import factory

from apps.content.models import Escena, ObjetoInteractivo
from apps.languages.tests.factories import LenguaFactory


class EscenaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Escena

    lengua = factory.SubFactory(LenguaFactory)
    nombre = factory.Sequence(lambda n: f"Cuarto {n}")
    fondo = "https://cdn.example.com/fondo.png"


class ObjetoInteractivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ObjetoInteractivo

    escena = factory.SubFactory(EscenaFactory)
    lengua = factory.SelfAttribute("escena.lengua")
    palabra = factory.Sequence(lambda n: f"palabra{n}")
    sprite = "https://cdn.example.com/sprite.png"
    audio_ogg = "https://cdn.example.com/audio.ogg"
    audio_m4a = "https://cdn.example.com/audio.m4a"
    x = 0
    y = 0
    width = 64
    height = 64
    estado = ObjetoInteractivo.Estado.PUBLICADO
