from django.core.management.base import BaseCommand

from events.images import attach_preview
from events.models import Flyer, ReportPhoto


class Command(BaseCommand):
    help = "Create small preview copies for flyers and photos that don't have one yet. Safe to run any time."

    def handle(self, *args, **options):
        made = 0
        for model in (Flyer, ReportPhoto):
            for obj in model.objects.filter(preview=""):
                attach_preview(obj)
                made += bool(obj.preview)
        self.stdout.write(f"Previews created: {made}")
