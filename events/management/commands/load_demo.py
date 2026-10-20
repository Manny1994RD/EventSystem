import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Role, User
from events import services
from events.models import Church, Event, EventType, Quarter

PASSWORD = "demo12345"


class Command(BaseCommand):
    help = "Add demo users and events to try the app. Do NOT run on the real server."

    def handle(self, *args, **options):
        call_command("setup_initial")
        churches = {c.name: c for c in Church.objects.all()}

        def user(username, first, role, church=None, admin=False):
            u, created = User.objects.get_or_create(username=username, defaults=dict(
                first_name=first, role=role, church=church, is_app_admin=admin, phone="809-555-0100"))
            if created:
                u.set_password(PASSWORD)
                u.save()
            return u

        user("regional", "Rosa (Regional)", Role.REGIONAL_REP, admin=True)
        user("overseer", "Pastor Juan (Overseer)", Role.OVERSEER)
        user("designer", "Luis (Designer)", Role.DESIGNER)
        reps = {}
        for name in churches:
            slug = name.lower().replace(" ", "")
            reps[name] = user(f"rep.{slug}", f"Rep {name}", Role.CHURCH_REP, churches[name])
            user(f"leader.{slug}", f"Leader {name}", Role.CHURCH_LEADER, churches[name])

        if Event.objects.exists():
            self.stdout.write("Demo events already exist.")
            return
        types = list(EventType.objects.all())
        nxt = Quarter.current().next()
        today = timezone.localdate()
        samples = [
            ("Santiago", "Confraternidad de jóvenes", 0, nxt.start + datetime.timedelta(days=9), "submit"),
            ("La Vega", "Seminario de familia", 1, nxt.start + datetime.timedelta(days=9), "submit"),
            ("Moca", "Limpieza del parque", 2, nxt.start + datetime.timedelta(days=15), "draft"),
            ("Puerto Plata", "Donación de sangre", 3, nxt.start + datetime.timedelta(days=20), "submit"),
            ("Jarabacoa", "Retiro de oración", 6, today + datetime.timedelta(days=12), "approve"),
            ("Santiago", "Seminario de liderazgo", 1, today + datetime.timedelta(days=25), "approve"),
        ]
        reviewer = User.objects.get(username="regional")
        for church, title, t, date, action in samples:
            e = Event.objects.create(
                church=churches[church], title=title, event_type=types[t], date=date,
                start_time=datetime.time(18, 0), end_time=datetime.time(20, 0),
                location=f"Iglesia de {church}", description="Evento de ejemplo.",
                contact_name=reps[church].first_name, contact_phone="809-555-0100", created_by=reps[church],
            )
            if action in ("submit", "approve"):
                services.submit_event(e, reps[church])
            if action == "approve":
                services.review_event(e, reviewer, "approve")
        self.stdout.write(self.style.SUCCESS(f"Demo data loaded. Every demo user's password is: {PASSWORD}"))
