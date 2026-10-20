from django.db import migrations, models


def mark_bible_socials(apps, schema_editor):
    EventType = apps.get_model("events", "EventType")
    EventType.objects.filter(models.Q(name_en__iexact="Bible social") | models.Q(name_es__iexact="Confraternidad bíblica")).update(
        full_report=True)


class Migration(migrations.Migration):
    dependencies = [("events", "0003_post_event_reports")]

    operations = [
        migrations.AddField(
            model_name="eventtype",
            name="full_report",
            field=models.BooleanField(
                default=False,
                help_text="Adds members who supported, fruits and Bible studies to the post-event report.",
                verbose_name="uses the full report (like Bible socials)",
            ),
        ),
        migrations.RenameField("eventreport", "people_served", "members_supporting"),
        migrations.RenameField("eventreport", "notes", "fragrance"),
        migrations.RunPython(mark_bible_socials, migrations.RunPython.noop),
    ]
