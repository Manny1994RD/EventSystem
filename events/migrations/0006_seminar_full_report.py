from django.db import migrations, models


def mark_seminars(apps, schema_editor):
    EventType = apps.get_model("events", "EventType")
    EventType.objects.filter(models.Q(name_en__iexact="Seminar") | models.Q(name_es__iexact="Seminario")).update(
        full_report=True)


class Migration(migrations.Migration):
    dependencies = [("events", "0005_report_labels")]

    operations = [migrations.RunPython(mark_seminars, migrations.RunPython.noop)]
