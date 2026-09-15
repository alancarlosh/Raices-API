from django.db import migrations, models


def backfill_glosa_es(apps, schema_editor):
    """Copia el placeholder en español que hoy vive en `palabra` a `glosa_es`,
    para no perder la glosa cuando `palabra` se reemplace por vocabulario
    totonaco real (ver apps/content/seed_data.py)."""
    ObjetoInteractivo = apps.get_model("content", "ObjetoInteractivo")
    ObjetoInteractivo.objects.filter(glosa_es="").update(glosa_es=models.F("palabra"))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0002_add_glosa_es"),
    ]

    operations = [
        migrations.RunPython(backfill_glosa_es, noop_reverse),
    ]
