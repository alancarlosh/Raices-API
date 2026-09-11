import os

from django.core.management.base import BaseCommand

from apps.accounts.models import Usuario


class Command(BaseCommand):
    help = (
        "Crea (o actualiza la contraseña de) un superusuario a partir de "
        "DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_PASSWORD/DJANGO_SUPERUSER_EMAIL. "
        "Pensado para correr en cada deploy (ver render.yaml), a diferencia de "
        "'createsuperuser --noinput' que falla si el usuario ya existe. Si las "
        "variables no están definidas, no hace nada (no rompe el build)."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_PASSWORD no están "
                    "definidos — se omite la creación del superusuario."
                )
            )
            return

        usuario, creado = Usuario.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        usuario.email = email or usuario.email
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.rol = Usuario.Rol.ADMIN
        usuario.set_password(password)
        usuario.save()

        self.stdout.write(
            self.style.SUCCESS(f"Superusuario '{username}' {'creado' if creado else 'actualizado'}.")
        )
