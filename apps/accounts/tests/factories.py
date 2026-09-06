import factory

from apps.accounts.models import Usuario


class UsuarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario

    username = factory.Sequence(lambda n: f"usuario{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    rol = Usuario.Rol.APRENDIZ
