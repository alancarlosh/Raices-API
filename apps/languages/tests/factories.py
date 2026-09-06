import factory

from apps.languages.models import Lengua


class LenguaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lengua

    nombre = factory.Sequence(lambda n: f"Lengua {n}")
    codigo = factory.Sequence(lambda n: f"len{n}")
