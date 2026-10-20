import datetime
import shutil
import sqlite3
import tarfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copy the database and the flyers into DATA_DIR/backups. Keeps the newest --keep backups."

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=14)

    def handle(self, *args, keep, **options):
        out_dir = Path(settings.BACKUP_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        work = out_dir / f"tmp-{stamp}"
        work.mkdir()
        try:
            # SQLite's backup API gives a consistent copy even while the app is running.
            src = sqlite3.connect(settings.DATABASES["default"]["NAME"])
            dst = sqlite3.connect(work / "db.sqlite3")
            with dst:
                src.backup(dst)
            src.close()
            dst.close()
            archive = out_dir / f"backup-{stamp}.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(work / "db.sqlite3", arcname="db.sqlite3")
                media = Path(settings.MEDIA_ROOT)
                if media.exists():
                    tar.add(media, arcname="media")
        finally:
            shutil.rmtree(work, ignore_errors=True)
        backups = sorted(out_dir.glob("backup-*.tar.gz"))
        for old in backups[:-keep]:
            old.unlink()
        self.stdout.write(self.style.SUCCESS(f"Backup written: {archive}"))
