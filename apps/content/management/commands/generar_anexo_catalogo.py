from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.content.anexo_catalogo import construir
from apps.content.seed_data import ESCENAS_SEED

VOCABULARIO = Path.home() / "Documents" / "Vocabulario_Totonaco_Casa_Rural.md"
SALIDA = Path.home() / "Documents" / "Anexo_B_Catalogo_Totonaco.md"


class Command(BaseCommand):
    help = (
        "Genera el Anexo B de la tesis (catálogo de términos con traducción al "
        "totonaco documentada) cruzando el archivo de vocabulario con la semilla de "
        "contenido. Falla en vez de escribir si los conteos no cuadran, si un término "
        "excluido ya no existe con ese nombre, o si algún término del catálogo no "
        "tiene fila en la semilla — ver apps/content/anexo_catalogo.py."
    )

    def add_arguments(self, parser):
        parser.add_argument("--vocabulario", type=Path, default=VOCABULARIO)
        parser.add_argument("--salida", type=Path, default=SALIDA)
        parser.add_argument(
            "--verificar",
            action="store_true",
            help="Solo comprueba que el anexo se puede generar y que coincide con el "
            "archivo ya escrito; no lo sobrescribe. Útil para saber si la tesis y la "
            "semilla siguen alineadas sin tocar nada.",
        )

    def handle(self, *args, **options):
        vocabulario: Path = options["vocabulario"]
        salida: Path = options["salida"]

        if not vocabulario.is_file():
            raise CommandError(
                f"No se encontró el archivo de vocabulario en {vocabulario}. "
                "Es la fuente del catálogo y vive fuera del repositorio; pásalo con "
                "--vocabulario si está en otro sitio."
            )

        glosas = {glosa for datos in ESCENAS_SEED.values() for _, glosa, _ in datos["objetos"]}

        try:
            markdown = construir(vocabulario.read_text(encoding="utf-8"), glosas)
        except ValueError as exc:
            # Las comprobaciones del módulo son el motivo de que esto exista:
            # mejor no generar nada que generar un anexo que contradiga al
            # cuerpo de la tesis.
            raise CommandError(str(exc)) from exc

        if options["verificar"]:
            if not salida.is_file():
                raise CommandError(f"No existe {salida}, así que no hay nada que verificar.")
            if salida.read_text(encoding="utf-8") != markdown:
                raise CommandError(
                    f"{salida} NO coincide con lo que se genera hoy desde el vocabulario y "
                    "la semilla. Corre el comando sin --verificar para regenerarlo, y "
                    "acuérdate de volver a convertirlo a LaTeX en la tesis."
                )
            self.stdout.write(self.style.SUCCESS(f"{salida} está al día."))
            return

        salida.write_text(markdown, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Anexo escrito en {salida}."))
        self.stdout.write(
            self.style.WARNING(
                "El formato de salida ya está convertido a LaTeX en la tesis: si cambió "
                "algo más que las filas, avisa a quien mantiene el documento."
            )
        )
