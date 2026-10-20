import os

from django.core.management.base import BaseCommand

from accounts.models import Role, User
from events.models import Church, EventType, SiteSettings

CHURCHES = [
    ("Santiago", "#2563eb"),
    ("La Vega", "#16a34a"),
    ("Moca", "#d97706"),
    ("Jarabacoa", "#9333ea"),
    ("Puerto Plata", "#dc2626"),
]

EVENT_TYPES = [
    ("Confraternidad bíblica", "Bible social"),
    ("Seminario", "Seminar"),
    ("Jornada de limpieza", "Cleanup"),
    ("Donación de sangre", "Blood donation"),
    ("Actividad juvenil", "Youth activity"),
    ("Evangelismo / alcance", "Outreach"),
    ("Otro", "Other"),
]


class Command(BaseCommand):
    help = "Create the starting churches, event types and settings. Safe to run more than once."

    def handle(self, *args, **options):
        SiteSettings.load()
        if not Church.objects.exists():
            for name, color in CHURCHES:
                Church.objects.create(name=name, color=color)
            self.stdout.write("Created churches.")
        if not EventType.objects.exists():
            for es, en in EVENT_TYPES:
                EventType.objects.create(name_es=es, name_en=en, full_report=(en in ("Bible social", "Seminar")))
            self.stdout.write("Created event types.")

        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")
        if username and password and not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username, password=password, first_name="Tech", last_name="Admin",
                role=Role.TECH_ADMIN, is_app_admin=True,
            )
            self.stdout.write(f"Created admin user '{username}'.")
