"""Business rules for events and flyers. Views call these; they handle permissions first."""

from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _

from accounts.models import Role, User

from . import emailing
from .models import (
    SLOT_STATUSES,
    Activity,
    ChangeRequest,
    Event,
    EventReport,
    EventStatus,
    Flyer,
    FlyerStatus,
    Notification,
    ReportPhoto,
    SiteSettings,
)


class DayFull(Exception):
    def __init__(self, date, events):
        self.date = date
        self.events = events
        super().__init__(f"{date} is full")


class NotAllowed(Exception):
    pass


# --- messages ---------------------------------------------------------------

def both_languages(text, **params):
    out = {}
    for lang in ("es", "en"):
        with translation.override(lang):
            values = {k: (str(v) if not callable(v) else v()) for k, v in params.items()}
            out[lang] = str(text) % values if values else str(text)
    return out["es"], out["en"]


def fmt_date(date):
    return date.strftime("%d/%m/%Y")


def log(event, actor, text, /, **params):
    es, en = both_languages(text, **params)
    Activity.objects.create(event=event, user=actor, text_es=es, text_en=en)


def notify(users, event, text, /, exclude=None, **params):
    es, en = both_languages(text, **params)
    seen = set()
    recipients = []
    for user in users:
        if user.pk in seen or (exclude is not None and user.pk == exclude.pk) or not user.is_active:
            continue
        seen.add(user.pk)
        recipients.append(user)
        Notification.objects.create(user=user, event=event, text_es=es, text_en=en)
    site = SiteSettings.load()
    if recipients and site.email_ready and site.email_notifications:
        # Send after the database change is saved, so a slow or failing email never breaks the action.
        transaction.on_commit(lambda: emailing.send_to_users(
            recipients, ("Eventos: aviso", "Church Events: update"), es, en, event=event, site=site))


def reviewers():
    return User.objects.filter(is_active=True, role__in=[Role.REGIONAL_REP, Role.OVERSEER])


def flyer_reviewers():
    return User.objects.filter(is_active=True, role__in=[Role.REGIONAL_REP, Role.OVERSEER])


def designers():
    return User.objects.filter(is_active=True, role=Role.DESIGNER)


def church_users(church):
    return User.objects.filter(is_active=True, church=church, role__in=[Role.CHURCH_LEADER, Role.CHURCH_REP])


# --- the daily limit --------------------------------------------------------

def events_on_day(date, exclude=None):
    qs = Event.objects.filter(date=date, status__in=SLOT_STATUSES).select_related("church", "event_type")
    if exclude is not None and exclude.pk:
        qs = qs.exclude(pk=exclude.pk)
    return list(qs)


def day_is_full(date, exclude=None):
    return len(events_on_day(date, exclude)) >= SiteSettings.load().max_events_per_day


# --- permissions ------------------------------------------------------------

def can_view(user, event):
    return user.sees_all_churches or (user.is_church_user and user.church_id == event.church_id)


def is_own_church(user, event):
    return user.is_church_user and user.church_id == event.church_id


def can_edit(user, event):
    if user.is_reviewer:
        return event.status not in (EventStatus.CANCELLED,)
    return is_own_church(user, event) and event.status in (EventStatus.DRAFT, EventStatus.CHANGES)


def can_upload_flyer(user, event):
    if event.status in (EventStatus.CANCELLED, EventStatus.DECLINED):
        return False
    return is_own_church(user, event) or user.is_reviewer


# --- event workflow ---------------------------------------------------------

@transaction.atomic
def submit_event(event, user, exception_reason=""):
    if not is_own_church(user, event) or event.status not in (EventStatus.DRAFT, EventStatus.CHANGES):
        raise NotAllowed
    taken = events_on_day(event.date, exclude=event)
    if len(taken) >= SiteSettings.load().max_events_per_day:
        if not exception_reason.strip():
            raise DayFull(event.date, taken)
        event.exception_requested = True
        event.exception_reason = exception_reason.strip()
    first_time = event.submitted_at is None
    event.status = EventStatus.SUBMITTED
    event.submitted_at = timezone.now()
    if timezone.localdate() > event.quarter.submission_deadline:
        event.is_late = True
    event.save()
    if event.exception_requested:
        log(event, user, _("Sent for approval, asking for an exception because the day is full: %(reason)s"),
            reason=event.exception_reason)
    else:
        log(event, user, _("Sent for approval."))
    msg = (_("%(church)s sent “%(title)s” (%(date)s) for approval.") if first_time
           else _("%(church)s sent “%(title)s” (%(date)s) again after making changes."))
    notify(reviewers(), event, msg, exclude=user, church=event.church, title=event.title, date=fmt_date(event.date))


@transaction.atomic
def withdraw_event(event, user):
    if not is_own_church(user, event) or event.status != EventStatus.SUBMITTED:
        raise NotAllowed
    event.status = EventStatus.DRAFT
    event.exception_requested = False
    event.save()
    log(event, user, _("Taken back to draft to make changes."))


@transaction.atomic
def review_event(event, user, decision, comment="", override=False):
    """decision: approve | changes | decline | cancel"""
    if not user.is_reviewer:
        raise NotAllowed
    if decision == "approve":
        if event.status not in (EventStatus.SUBMITTED, EventStatus.CHANGES):
            raise NotAllowed
        if day_is_full(event.date, exclude=event) and not (override or event.limit_override):
            raise DayFull(event.date, events_on_day(event.date, exclude=event))
        if override and day_is_full(event.date, exclude=event):
            event.limit_override = True
            event.override_by = user
        event.status = EventStatus.APPROVED
        text = _("Approved.")
        church_msg = _("“%(title)s” (%(date)s) was approved by %(user)s.")
    elif decision == "changes":
        if event.status not in (EventStatus.SUBMITTED, EventStatus.APPROVED):
            raise NotAllowed
        event.status = EventStatus.CHANGES
        text = _("Changes requested.")
        church_msg = _("%(user)s asked for changes to “%(title)s” (%(date)s). Open it to see what to fix.")
    elif decision == "decline":
        if event.status not in (EventStatus.SUBMITTED, EventStatus.CHANGES):
            raise NotAllowed
        event.status = EventStatus.DECLINED
        text = _("Declined.")
        church_msg = _("“%(title)s” (%(date)s) was declined by %(user)s.")
    elif decision == "cancel":
        if event.status in (EventStatus.CANCELLED, EventStatus.DRAFT):
            raise NotAllowed
        event.status = EventStatus.CANCELLED
        text = _("Cancelled.")
        church_msg = _("“%(title)s” (%(date)s) was cancelled by %(user)s.")
    else:
        raise NotAllowed
    event.review_comment = comment.strip()
    event.reviewed_by = user
    event.reviewed_at = timezone.now()
    event.save()
    if comment.strip():
        log(event, user, _("%(action)s Comment: %(comment)s"), action=text, comment=comment.strip())
    else:
        log(event, user, text)
    notify(church_users(event.church), event, church_msg, exclude=user,
           title=event.title, date=fmt_date(event.date), user=user)
    if event.limit_override and decision == "approve":
        log(event, user, _("Approved as an exception to the daily limit."))


@transaction.atomic
def reviewer_update(event, user, old_values, override=False):
    """A reviewer changed the event directly: applies right away, no re-approval; the church is told."""
    if not user.is_reviewer:
        raise NotAllowed
    if old_values.get("date") != event.date and event.status in SLOT_STATUSES:
        if day_is_full(event.date, exclude=event):
            if not override:
                raise DayFull(event.date, events_on_day(event.date, exclude=event))
            event.limit_override = True
            event.override_by = user
    event.save()
    changes = []
    if old_values.get("date") != event.date:
        changes.append(f"{fmt_date(old_values['date'])} → {fmt_date(event.date)}")
    if old_values.get("start_time") != event.start_time:
        changes.append(f"{old_values['start_time']:%H:%M} → {event.start_time:%H:%M}")
    if old_values.get("location") != event.location:
        changes.append(f"{old_values['location']} → {event.location}")
    summary = "; ".join(changes) or "—"
    log(event, user, _("Updated by %(user)s: %(changes)s"), user=user, changes=summary)
    if event.status != EventStatus.DRAFT:
        notify(church_users(event.church), event,
               _("%(user)s updated “%(title)s”: %(changes)s"), exclude=user,
               user=user, title=event.title, changes=summary)


@transaction.atomic
def request_change(event, user, change):
    if not is_own_church(user, event) or event.status != EventStatus.APPROVED:
        raise NotAllowed
    if event.pending_change:
        raise NotAllowed
    change.event = event
    change.requested_by = user
    change.save()
    if change.cancel:
        text = _("%(church)s asks to CANCEL “%(title)s” (%(date)s).")
    else:
        text = _("%(church)s asks to change “%(title)s” (%(date)s).")
    log(event, user, _("Change requested: %(reason)s"), reason=change.reason)
    notify(reviewers(), event, text, exclude=user, church=event.church, title=event.title, date=fmt_date(event.date))


@transaction.atomic
def decide_change(change, user, approve, comment="", override=False):
    if not user.is_reviewer or change.status != ChangeRequest.Status.PENDING:
        raise NotAllowed
    event = change.event
    if approve:
        if change.cancel:
            event.status = EventStatus.CANCELLED
        else:
            new_date = change.new_date or event.date
            if new_date != event.date and day_is_full(new_date, exclude=event):
                if not override:
                    raise DayFull(new_date, events_on_day(new_date, exclude=event))
                event.limit_override = True
                event.override_by = user
            event.date = new_date
            event.start_time = change.new_start_time or event.start_time
            event.end_time = change.new_end_time or event.end_time
            event.location = change.new_location or event.location
        event.save()
        change.status = ChangeRequest.Status.APPROVED
        church_text = _("Your change to “%(title)s” was approved by %(user)s.")
        log(event, user, _("Change approved."))
    else:
        change.status = ChangeRequest.Status.DECLINED
        church_text = _("Your change to “%(title)s” was not approved by %(user)s. The event stays as it was.")
        log(event, user, _("Change not approved. %(comment)s"), comment=comment)
    change.decided_by = user
    change.decided_at = timezone.now()
    change.decision_comment = comment.strip()
    change.save()
    notify(church_users(event.church), event, church_text, exclude=user, title=event.title, user=user)


# --- flyers -----------------------------------------------------------------

@transaction.atomic
def upload_flyer(event, user, uploaded_file):
    designer_fix = user.is_designer
    if designer_fix:
        if event.flyer_status != FlyerStatus.DESIGNER:
            raise NotAllowed
    elif not can_upload_flyer(user, event):
        raise NotAllowed
    last = event.latest_flyer
    flyer = Flyer.objects.create(
        event=event, file=uploaded_file, original_name=uploaded_file.name[:255],
        version=(last.version + 1) if last else 1,
        source=Flyer.Source.DESIGNER if designer_fix else Flyer.Source.CHURCH,
        uploaded_by=user,
    )
    settings = SiteSettings.load()
    params = dict(title=event.title, date=fmt_date(event.date), church=event.church, version=flyer.version)
    if designer_fix and settings.auto_approve_designer_flyers:
        event.flyer_status = FlyerStatus.APPROVED
        log(event, user, _("Designer uploaded the fixed flyer (version %(version)s). Approved automatically."), **params)
        notify(list(church_users(event.church)) + list(flyer_reviewers()), event,
               _("The fixed flyer for “%(title)s” is ready and approved."), exclude=user, **params)
    elif designer_fix:
        event.flyer_status = FlyerStatus.PENDING
        log(event, user, _("Designer uploaded the fixed flyer (version %(version)s)."), **params)
        notify(flyer_reviewers(), event, _("The designer fixed the flyer for “%(title)s” (%(church)s). It needs your final OK."),
               exclude=user, **params)
    elif user.can_review_flyers:
        event.flyer_status = FlyerStatus.APPROVED
        log(event, user, _("Flyer uploaded and approved by %(user)s (version %(version)s)."), user=user, **params)
    else:
        event.flyer_status = FlyerStatus.PENDING
        log(event, user, _("Flyer uploaded (version %(version)s)."), **params)
        notify(flyer_reviewers(), event, _("New flyer from %(church)s for “%(title)s” (%(date)s) to review."),
               exclude=user, **params)
    event.save()
    return flyer


@transaction.atomic
def review_flyer(event, user, approve, notes=""):
    if not user.can_review_flyers or event.flyer_status != FlyerStatus.PENDING:
        raise NotAllowed
    flyer = event.latest_flyer
    params = dict(title=event.title, date=fmt_date(event.date), church=event.church, notes=notes.strip())
    if approve:
        event.flyer_status = FlyerStatus.APPROVED
        log(event, user, _("Flyer approved."))
        notify(church_users(event.church), event, _("The flyer for “%(title)s” was approved."), exclude=user, **params)
    else:
        if not notes.strip():
            raise NotAllowed
        event.flyer_status = FlyerStatus.DESIGNER
        flyer.review_notes = notes.strip()
        flyer.save()
        log(event, user, _("Flyer sent to the designer: %(notes)s"), **params)
        notify(designers(), event, _("Flyer for “%(title)s” (%(church)s) needs adjustments: %(notes)s"),
               exclude=user, **params)
        notify(church_users(event.church), event,
               _("The flyer for “%(title)s” was sent to the graphic designer for adjustments."), exclude=user, **params)
    event.save()


# --- post-event reports -----------------------------------------------------

def can_write_report(user, event):
    return (is_own_church(user, event) and event.status == EventStatus.APPROVED
            and event.date <= timezone.localdate())


@transaction.atomic
def save_report(event, user, form, submit=False):
    if not can_write_report(user, event):
        raise NotAllowed
    report = form.save(commit=False)
    if report.status == EventReport.Status.SUBMITTED:
        raise NotAllowed
    report.event = event
    report.save()
    form.save_m2m()
    for f in form.cleaned_data.get("photos") or []:
        ReportPhoto.objects.create(report=report, file=f, uploaded_by=user)
    if submit:
        report.status = EventReport.Status.SUBMITTED
        report.submitted_by = user
        report.submitted_at = timezone.now()
        report.save()
        log(event, user, _("Post-event report sent."))
        notify(reviewers(), event, _("%(church)s sent the report for “%(title)s” (%(date)s): %(n)s attended."),
               exclude=user, church=event.church, title=event.title, date=fmt_date(event.date),
               n=report.total_attendance)
    return report


@transaction.atomic
def return_report(report, user, comment):
    if not user.is_reviewer or report.status != EventReport.Status.SUBMITTED or not comment.strip():
        raise NotAllowed
    event = report.event
    report.status = EventReport.Status.DRAFT
    report.review_comment = comment.strip()
    report.save()
    log(event, user, _("Report sent back for corrections: %(comment)s"), comment=comment.strip())
    notify(church_users(event.church), event,
           _("%(user)s asked for corrections to the report for “%(title)s”: %(comment)s"),
           exclude=user, user=user, title=event.title, comment=comment.strip())
