"""Daily email reminders. Runs from the scheduler container; does nothing while email is off."""

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from events import emailing, services
from events.models import (
    SLOT_STATUSES, Church, Event, EventReport, EventStatus, FlyerStatus, Quarter, ReminderLog, SiteSettings,
)

DEADLINE_DAYS = (14, 7, 2, 0)


def both(fn):
    out = []
    for lang in ("es", "en"):
        with translation.override(lang):
            out.append(fn())
    return out


class Command(BaseCommand):
    help = "Email reminders about the quarter deadline and flyer deadlines."

    def handle(self, *args, **options):
        site = SiteSettings.load()
        if not (site.email_ready and site.email_reminders):
            self.stdout.write("Email reminders are off.")
            return
        sent = self.quarter_reminders(site) + self.flyer_reminders(site) + self.report_reminders(site)
        self.stdout.write(f"Reminder emails sent: {sent}")

    def once(self, key):
        _obj, created = ReminderLog.objects.get_or_create(key=key)
        return created

    def quarter_reminders(self, site):
        today = timezone.localdate()
        quarter = Quarter.current().next()
        days = (quarter.submission_deadline - today).days
        if days not in DEADLINE_DAYS:
            return 0
        sent = 0
        for church in Church.objects.filter(is_active=True):
            events = Event.objects.filter(church=church, quarter=quarter)
            nothing_sent = not events.filter(status__in=SLOT_STATUSES).exists()
            drafts = events.filter(status__in=[EventStatus.DRAFT, EventStatus.CHANGES]).count()
            if not (nothing_sent or drafts):
                continue
            if not self.once(f"quarter:{quarter.pk}:{church.pk}:{days}"):
                continue
            deadline = services.fmt_date(quarter.submission_deadline)

            def text():
                lines = [_("Reminder for %(church)s: events for %(q)s must be sent by %(d)s.")
                         % {"church": church, "q": quarter.label, "d": deadline}]
                if nothing_sent:
                    lines.append(_("Your church has not sent any events yet."))
                if drafts:
                    lines.append(_("You have %(n)s event(s) still in draft — remember to press “Send for approval”.")
                                 % {"n": drafts})
                return "\n".join(lines)

            es, en = both(text)
            subject = both(lambda: _("Reminder: events due %(d)s") % {"d": deadline})
            sent += emailing.send_to_users(services.church_users(church), subject, es, en, site=site)
        return sent

    def flyer_reminders(self, site):
        today = timezone.localdate()
        sent = 0
        events = Event.objects.filter(status__in=SLOT_STATUSES, date__gt=today).filter(
            Q(flyer_status=FlyerStatus.NONE) | Q(flyer_status=FlyerStatus.DESIGNER)).select_related("church")
        for event in events:
            if today == event.flyer_due_date:
                kind = "due"
            elif today == event.flyer_final_date:
                kind = "final"
            else:
                continue
            if not self.once(f"flyer:{event.pk}:{kind}:{event.date}"):
                continue
            params = {"title": event.title, "date": services.fmt_date(event.date)}

            def text():
                if kind == "due":
                    return _("The flyer for “%(title)s” (%(date)s) is due today. Please upload it in the app.") % params
                return _("LAST DAY: the flyer for “%(title)s” (%(date)s) must be uploaded today.") % params

            es, en = both(text)
            subject = both(lambda: _("Flyer reminder: %(title)s") % params)
            users = (services.designers() if event.flyer_status == FlyerStatus.DESIGNER
                     else services.church_users(event.church))
            sent += emailing.send_to_users(users, subject, es, en, event=event, site=site)
        return sent

    def report_reminders(self, site):
        """The day after an event, and again a week later, if the post-event report hasn't been sent."""
        import datetime

        today = timezone.localdate()
        sent = 0
        for days in (1, 7):
            day = today - datetime.timedelta(days=days)
            events = Event.objects.filter(status=EventStatus.APPROVED, date=day).exclude(
                report__status=EventReport.Status.SUBMITTED).select_related("church")
            for event in events:
                if not self.once(f"report:{event.pk}:{days}"):
                    continue
                params = {"title": event.title, "date": services.fmt_date(event.date)}
                es, en = both(lambda: _("Please send the post-event report for “%(title)s” (%(date)s): attendance, "
                                        "fruits, Bible studies, invites, cost and photos.") % params)
                subject = both(lambda: _("Post-event report: %(title)s") % params)
                sent += emailing.send_to_users(services.church_users(event.church), subject, es, en,
                                               event=event, site=site)
        return sent
