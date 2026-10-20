import calendar
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from . import emailing, services
from .forms import (
    ChangeRequestForm,
    ChurchForm,
    EmailSettingsForm,
    EventForm,
    EventTypeForm,
    FlyerUploadForm,
    QuarterDeadlineForm,
    SiteSettingsForm,
)
from .models import (
    SLOT_STATUSES,
    ChangeRequest,
    Church,
    Event,
    EventStatus,
    EventType,
    Flyer,
    FlyerStatus,
    Notification,
    Quarter,
    SiteSettings,
)


def reviewer_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_reviewer:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def manager_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.user.can_manage:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def get_event_for(user, pk):
    event = get_object_or_404(Event.objects.select_related("church", "event_type", "quarter"), pk=pk)
    if not services.can_view(user, event):
        raise PermissionDenied
    return event


def show_day_full(request, err):
    names = ", ".join(f"{e.title} ({e.church})" for e in err.events)
    messages.error(
        request,
        _("%(date)s already has %(count)s events in the region: %(names)s.")
        % {"date": services.fmt_date(err.date), "count": len(err.events), "names": names},
    )


# --- home -------------------------------------------------------------------

@login_required
def home(request):
    user = request.user
    today = timezone.localdate()
    current = Quarter.current()
    upcoming = current.next()
    ctx = {"current": current, "upcoming": upcoming, "todo": []}
    todo = ctx["todo"]

    if user.is_church_user and user.church:
        mine = Event.objects.filter(church=user.church)
        ctx["church"] = user.church
        drafts = mine.filter(status=EventStatus.DRAFT, date__gte=today).count()
        changes = mine.filter(status=EventStatus.CHANGES).count()
        no_flyer = [e for e in mine.filter(status__in=SLOT_STATUSES, date__gte=today)
                    .exclude(flyer_status__in=[FlyerStatus.APPROVED, FlyerStatus.PENDING, FlyerStatus.DESIGNER])
                    if e.flyer_alert]
        upcoming_count = mine.filter(quarter=upcoming).exclude(status=EventStatus.CANCELLED).count()
        if changes:
            todo.append(("danger", _("%(n)s event(s) need changes. Open them to see what to fix.") % {"n": changes},
                         "events:list", "?status=changes"))
        if drafts:
            todo.append(("warning", _("%(n)s event(s) are still drafts and have NOT been sent.") % {"n": drafts},
                         "events:list", "?status=draft"))
        if no_flyer:
            todo.append(("warning", _("%(n)s event(s) need a flyer soon.") % {"n": len(no_flyer)},
                         "events:list", "?flyer=missing"))
        if upcoming_count == 0:
            todo.append(("info", _("You haven't added any events for %(q)s yet. Due by %(d)s.")
                         % {"q": upcoming.label, "d": services.fmt_date(upcoming.submission_deadline)},
                         "events:create", ""))
        ctx["next_events"] = mine.filter(date__gte=today).exclude(
            status__in=[EventStatus.CANCELLED, EventStatus.DECLINED]).select_related("event_type")[:6]

    if user.is_reviewer:
        waiting = Event.objects.filter(status=EventStatus.SUBMITTED).count()
        change_reqs = ChangeRequest.objects.filter(status=ChangeRequest.Status.PENDING).count()
        if waiting:
            todo.append(("warning", _("%(n)s event(s) are waiting for your approval.") % {"n": waiting},
                         "events:review_queue", ""))
        if change_reqs:
            todo.append(("warning", _("%(n)s change request(s) are waiting for you.") % {"n": change_reqs},
                         "events:review_queue", "#changes"))
    if user.can_review_flyers:
        flyers = Event.objects.filter(flyer_status=FlyerStatus.PENDING).count()
        if flyers:
            todo.append(("warning", _("%(n)s flyer(s) are waiting for your review.") % {"n": flyers},
                         "events:flyer_queue", ""))
    if user.is_designer:
        fixes = Event.objects.filter(flyer_status=FlyerStatus.DESIGNER).count()
        if fixes:
            todo.append(("warning", _("%(n)s flyer(s) need your adjustments.") % {"n": fixes},
                         "events:designer_queue", ""))

    if user.sees_all_churches:
        ctx["next_events"] = Event.objects.filter(date__gte=today, status=EventStatus.APPROVED).select_related(
            "church", "event_type")[:8]
    return render(request, "events/home.html", ctx)


# --- events -----------------------------------------------------------------

@login_required
def event_list(request):
    user = request.user
    quarter_id = request.GET.get("quarter")
    quarter = Quarter.objects.filter(pk=quarter_id).first() if quarter_id else None
    if quarter is None:
        quarter = Quarter.current().next() if user.is_church_user else Quarter.current()
    qs = Event.objects.filter(quarter=quarter).select_related("church", "event_type")
    if not user.sees_all_churches:
        qs = qs.filter(church=user.church)
    status = request.GET.get("status")
    if status in EventStatus.values:
        qs = qs.filter(status=status)
    church_id = request.GET.get("church")
    if church_id and user.sees_all_churches:
        qs = qs.filter(church_id=church_id)
    events = list(qs)
    if request.GET.get("flyer") == "missing":
        events = [e for e in events if e.flyer_status != FlyerStatus.APPROVED]
    drafts = [e for e in events if e.status == EventStatus.DRAFT and services.is_own_church(user, e)]
    ctx = {
        "quarter": quarter,
        "prev_q": quarter.previous(),
        "next_q": quarter.next(),
        "events": events,
        "drafts_count": len(drafts),
        "statuses": EventStatus.choices,
        "churches": Church.objects.all() if user.sees_all_churches else None,
        "status": status,
        "church_id": church_id,
    }
    return render(request, "events/event_list.html", ctx)


@login_required
def event_create(request):
    user = request.user
    if not (user.is_church_user and user.church):
        raise PermissionDenied
    initial = {"contact_name": user.get_full_name(), "contact_phone": user.phone}
    if request.GET.get("date"):
        initial["date"] = request.GET["date"]
    form = EventForm(request.POST or None, user=user, initial=initial)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.church = user.church
        event.created_by = user
        event.save()
        services.log(event, user, gettext_lazy("Event created as a draft."))
        if services.day_is_full(event.date, exclude=event):
            messages.warning(request, _("Saved. Careful: that day is already full in the region. "
                                        "You will need to pick another date or ask for an exception."))
        else:
            messages.success(request, _("Saved as a draft. Remember to press “Send for approval”."))
        return redirect("events:detail", pk=event.pk)
    return render(request, "events/event_form.html", {"form": form, "creating": True})


@login_required
def event_edit(request, pk):
    user = request.user
    event = get_event_for(user, pk)
    if not services.can_edit(user, event):
        raise PermissionDenied
    old = {"date": event.date, "start_time": event.start_time, "location": event.location}
    form = EventForm(request.POST or None, instance=event, user=user)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        if user.is_reviewer and not services.is_own_church(user, event):
            try:
                services.reviewer_update(event, user, old, override=bool(request.POST.get("override")))
            except services.DayFull as err:
                show_day_full(request, err)
                return render(request, "events/event_form.html",
                              {"form": form, "event": event, "need_override": True})
        else:
            event.save()
            services.log(event, user, gettext_lazy("Event details edited."))
        messages.success(request, _("Changes saved."))
        return redirect("events:detail", pk=event.pk)
    return render(request, "events/event_form.html", {"form": form, "event": event})


@login_required
def event_detail(request, pk):
    user = request.user
    event = get_event_for(user, pk)
    own = services.is_own_church(user, event)
    ctx = {
        "event": event,
        "own": own,
        "can_edit": services.can_edit(user, event),
        "can_submit": own and event.status in (EventStatus.DRAFT, EventStatus.CHANGES),
        "can_withdraw": own and event.status == EventStatus.SUBMITTED,
        "can_request_change": own and event.status == EventStatus.APPROVED and not event.pending_change,
        "can_upload_flyer": services.can_upload_flyer(user, event) or
                            (user.is_designer and event.flyer_status == FlyerStatus.DESIGNER),
        "can_review_flyer": user.can_review_flyers and event.flyer_status == FlyerStatus.PENDING,
        "day_full": services.day_is_full(event.date, exclude=event),
        "same_day": services.events_on_day(event.date, exclude=event),
        "flyers": event.flyers.select_related("uploaded_by"),
        "activity": event.activity.select_related("user")[:30],
        "change": event.pending_change,
        "upload_form": FlyerUploadForm(),
        "change_form": ChangeRequestForm(),
        "max_per_day": SiteSettings.load().max_events_per_day,
    }
    return render(request, "events/event_detail.html", ctx)


@login_required
@require_POST
def event_delete(request, pk):
    event = get_event_for(request.user, pk)
    if not services.is_own_church(request.user, event) or event.status != EventStatus.DRAFT:
        raise PermissionDenied
    event.delete()
    messages.success(request, _("Draft deleted."))
    return redirect("events:list")


@login_required
@require_POST
def event_submit(request, pk):
    event = get_event_for(request.user, pk)
    try:
        services.submit_event(event, request.user, request.POST.get("exception_reason", ""))
    except services.DayFull as err:
        show_day_full(request, err)
        messages.info(request, _("Pick another date, or write below why you need this day and ask for an exception."))
        return redirect("events:detail", pk=event.pk)
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("Sent! The Regional Events Rep and the Overseer have been notified."))
    return redirect("events:detail", pk=event.pk)


@login_required
@require_POST
def submit_all(request):
    user = request.user
    if not user.is_church_user:
        raise PermissionDenied
    quarter = get_object_or_404(Quarter, pk=request.POST.get("quarter"))
    sent, blocked = 0, []
    for event in Event.objects.filter(church=user.church, quarter=quarter,
                                      status__in=[EventStatus.DRAFT, EventStatus.CHANGES]):
        try:
            services.submit_event(event, user)
            sent += 1
        except services.DayFull:
            blocked.append(event)
    if sent:
        messages.success(request, _("%(n)s event(s) sent for approval.") % {"n": sent})
    for event in blocked:
        messages.error(request, _("“%(title)s” was NOT sent: %(date)s is already full. Open it to pick another "
                                  "date or ask for an exception.") % {"title": event.title,
                                                                     "date": services.fmt_date(event.date)})
    return redirect(f"{reverse('events:list')}?quarter={quarter.pk}")


@login_required
@require_POST
def event_withdraw(request, pk):
    event = get_event_for(request.user, pk)
    try:
        services.withdraw_event(event, request.user)
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("The event is a draft again. Make your changes and send it again."))
    return redirect("events:detail", pk=event.pk)


@reviewer_required
@require_POST
def event_review(request, pk):
    event = get_event_for(request.user, pk)
    decision = request.POST.get("decision")
    comment = request.POST.get("comment", "")
    if decision in ("changes", "decline") and not comment.strip():
        messages.error(request, _("Please write a comment so the church knows why."))
        return redirect("events:detail", pk=event.pk)
    try:
        services.review_event(event, request.user, decision, comment, override=bool(request.POST.get("override")))
    except services.DayFull as err:
        show_day_full(request, err)
        messages.info(request, _("To approve it anyway, tick “Approve as an exception” and press Approve again."))
        return redirect("events:detail", pk=event.pk)
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("Done. The church has been notified."))
    if request.POST.get("next") == "detail":
        return redirect("events:detail", pk=event.pk)
    return redirect("events:review_queue")


# --- change requests ---------------------------------------------------------

@login_required
@require_POST
def change_request(request, pk):
    event = get_event_for(request.user, pk)
    form = ChangeRequestForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for e in errors:
                messages.error(request, e)
        return redirect("events:detail", pk=event.pk)
    try:
        services.request_change(event, request.user, form.save(commit=False))
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("Your request was sent. The event stays as it is until it is approved."))
    return redirect("events:detail", pk=event.pk)


@reviewer_required
@require_POST
def change_decide(request, pk):
    change = get_object_or_404(ChangeRequest, pk=pk)
    try:
        services.decide_change(change, request.user, request.POST.get("decision") == "approve",
                               request.POST.get("comment", ""), override=bool(request.POST.get("override")))
    except services.DayFull as err:
        show_day_full(request, err)
        messages.info(request, _("To approve it anyway, tick “Approve as an exception”."))
        return redirect("events:detail", pk=change.event_id)
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("Done. The church has been notified."))
    return redirect("events:detail", pk=change.event_id)


# --- flyers -----------------------------------------------------------------

@login_required
@require_POST
def flyer_upload(request, pk):
    event = get_event_for(request.user, pk)
    form = FlyerUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        for e in form.errors.get("file", []):
            messages.error(request, e)
        return redirect("events:detail", pk=event.pk)
    try:
        services.upload_flyer(event, request.user, form.cleaned_data["file"])
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("Flyer uploaded."))
    return redirect("events:detail", pk=event.pk)


@login_required
@require_POST
def flyer_review(request, pk):
    event = get_event_for(request.user, pk)
    approve = request.POST.get("decision") == "approve"
    notes = request.POST.get("notes", "")
    if not approve and not notes.strip():
        messages.error(request, _("Write what the designer needs to adjust."))
        return redirect("events:detail", pk=event.pk)
    try:
        services.review_flyer(event, request.user, approve, notes)
    except services.NotAllowed:
        raise PermissionDenied
    messages.success(request, _("Flyer approved.") if approve else _("Sent to the graphic designer."))
    if request.POST.get("next") == "queue":
        return redirect("events:flyer_queue")
    return redirect("events:detail", pk=event.pk)


def flyer_file(request, pk):
    flyer = get_object_or_404(Flyer.objects.select_related("event"), pk=pk)
    event = flyer.event
    public = (event.status == EventStatus.APPROVED and event.flyer_status == FlyerStatus.APPROVED
              and event.latest_flyer.pk == flyer.pk)
    if not public:
        if not request.user.is_authenticated or not services.can_view(request.user, event):
            raise Http404
    try:
        return FileResponse(flyer.file.open("rb"), filename=flyer.original_name,
                            as_attachment=request.GET.get("download") == "1")
    except FileNotFoundError:
        raise Http404


# --- queues -----------------------------------------------------------------

@reviewer_required
def review_queue(request):
    events = Event.objects.filter(status=EventStatus.SUBMITTED).select_related("church", "event_type")
    changes = ChangeRequest.objects.filter(status=ChangeRequest.Status.PENDING).select_related(
        "event", "event__church", "requested_by")
    return render(request, "events/review_queue.html", {"events": events, "changes": changes})


@login_required
def flyer_queue(request):
    if not request.user.can_review_flyers:
        raise PermissionDenied
    events = Event.objects.filter(flyer_status=FlyerStatus.PENDING).select_related("church").order_by("date")
    return render(request, "events/flyer_queue.html", {"events": events})


@login_required
def designer_queue(request):
    if not (request.user.is_designer or request.user.can_review_flyers):
        raise PermissionDenied
    events = Event.objects.filter(flyer_status=FlyerStatus.DESIGNER).select_related("church").order_by("date")
    return render(request, "events/designer_queue.html", {"events": events})


# --- regional dashboard -----------------------------------------------------

@login_required
def regional(request):
    if not request.user.sees_all_churches:
        raise PermissionDenied
    quarter_id = request.GET.get("quarter")
    quarter = Quarter.objects.filter(pk=quarter_id).first() if quarter_id else Quarter.current().next()
    rows = []
    for church in Church.objects.filter(is_active=True):
        qs = Event.objects.filter(church=church, quarter=quarter)
        counts = qs.aggregate(
            total=Count("id", filter=~Q(status__in=[EventStatus.CANCELLED])),
            draft=Count("id", filter=Q(status=EventStatus.DRAFT)),
            submitted=Count("id", filter=Q(status=EventStatus.SUBMITTED)),
            changes=Count("id", filter=Q(status=EventStatus.CHANGES)),
            approved=Count("id", filter=Q(status=EventStatus.APPROVED)),
            late=Count("id", filter=Q(is_late=True)),
            flyers_ok=Count("id", filter=Q(flyer_status=FlyerStatus.APPROVED, status=EventStatus.APPROVED)),
        )
        sent = counts["submitted"] + counts["changes"] + counts["approved"]
        if sent == 0:
            state = "missing"
        elif counts["late"]:
            state = "late"
        else:
            state = "ok"
        rows.append({"church": church, "state": state, **counts})
    full_days = (Event.objects.filter(quarter=quarter, status__in=SLOT_STATUSES).values("date")
                 .annotate(n=Count("id")).filter(n__gte=SiteSettings.load().max_events_per_day).order_by("date"))
    overrides = Event.objects.filter(quarter=quarter, limit_override=True).select_related("church", "override_by")
    exceptions = Event.objects.filter(quarter=quarter, exception_requested=True,
                                      status=EventStatus.SUBMITTED).select_related("church")
    return render(request, "events/regional.html", {
        "quarter": quarter, "prev_q": quarter.previous(), "next_q": quarter.next(), "rows": rows,
        "full_days": full_days, "overrides": overrides, "exceptions": exceptions,
    })


# --- calendar ---------------------------------------------------------------

def _month_from_request(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get("y", today.year))
        month = int(request.GET.get("m", today.month))
        datetime.date(year, month, 1)
    except ValueError:
        year, month = today.year, today.month
    return year, month


def _calendar_context(year, month, events):
    by_day = {}
    for e in events:
        by_day.setdefault(e.date, []).append(e)
    weeks = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(year, month):
        weeks.append([{"date": d, "in_month": d.month == month, "events": by_day.get(d, [])} for d in week])
    first = datetime.date(year, month, 1)
    prev_m = (first - datetime.timedelta(days=1)).replace(day=1)
    next_m = (first + datetime.timedelta(days=32)).replace(day=1)
    return {"weeks": weeks, "month": first, "prev_m": prev_m, "next_m": next_m, "today": timezone.localdate(),
            "max_per_day": SiteSettings.load().max_events_per_day}


@login_required
def calendar_view(request):
    year, month = _month_from_request(request)
    qs = Event.objects.filter(date__year=year, date__month=month).select_related("church", "event_type")
    user = request.user
    own_drafts = Q(status=EventStatus.DRAFT, church=user.church) if user.church_id else Q(pk__in=[])
    events = qs.filter(Q(status__in=SLOT_STATUSES) | own_drafts)
    ctx = _calendar_context(year, month, events)
    ctx["churches"] = Church.objects.filter(is_active=True)
    return render(request, "events/calendar.html", ctx)


def public_calendar(request):
    year, month = _month_from_request(request)
    events = Event.objects.filter(date__year=year, date__month=month, status=EventStatus.APPROVED).select_related(
        "church", "event_type")
    ctx = _calendar_context(year, month, events)
    ctx["churches"] = Church.objects.filter(is_active=True)
    ctx["public"] = True
    ctx["list_events"] = events
    return render(request, "events/public_calendar.html", ctx)


def public_event(request, pk):
    event = get_object_or_404(Event.objects.select_related("church", "event_type"), pk=pk,
                              status=EventStatus.APPROVED)
    flyer = event.latest_flyer if event.flyer_status == FlyerStatus.APPROVED else None
    return render(request, "events/public_event.html", {"event": event, "flyer": flyer, "public": True})


@login_required
def day_check(request):
    """Used by the event form to show what's already booked on the chosen day."""
    try:
        date = datetime.date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return JsonResponse({"ok": False})
    exclude = Event.objects.filter(pk=request.GET.get("exclude")).first() if request.GET.get("exclude") else None
    taken = services.events_on_day(date, exclude=exclude)
    limit = SiteSettings.load().max_events_per_day
    return JsonResponse({
        "ok": True,
        "count": len(taken),
        "limit": limit,
        "full": len(taken) >= limit,
        "events": [{"title": e.title, "church": e.church.name, "time": e.start_time.strftime("%H:%M")} for e in taken],
    })


# --- notifications ----------------------------------------------------------

@login_required
def notifications(request):
    items = list(request.user.notifications.select_related("event")[:100])
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "events/notifications.html", {"items": items})


@login_required
def notification_open(request, pk):
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    note.is_read = True
    note.save(update_fields=["is_read"])
    if note.event_id:
        return redirect("events:detail", pk=note.event_id)
    return redirect("events:notifications")


# --- settings (admins) ------------------------------------------------------

@manager_required
def settings_home(request):
    site = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, instance=site)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Settings saved."))
        return redirect("events:settings")
    current = Quarter.current()
    quarters = [current.previous(), current, current.next(), current.next().next()]
    return render(request, "events/settings.html", {
        "form": form, "churches": Church.objects.annotate(n_users=Count("users")),
        "types": EventType.objects.all(), "quarters": quarters, "site": site,
    })


@manager_required
def church_edit(request, pk=None):
    church = get_object_or_404(Church, pk=pk) if pk else None
    form = ChurchForm(request.POST or None, instance=church)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Church saved."))
        return redirect("events:settings")
    return render(request, "events/simple_form.html", {
        "form": form, "title": _("Edit church") if church else _("Add a church")})


@manager_required
def event_type_edit(request, pk=None):
    obj = get_object_or_404(EventType, pk=pk) if pk else None
    form = EventTypeForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Event type saved."))
        return redirect("events:settings")
    return render(request, "events/simple_form.html", {
        "form": form, "title": _("Edit event type") if obj else _("Add an event type")})


@manager_required
def quarter_edit(request, pk):
    quarter = get_object_or_404(Quarter, pk=pk)
    form = QuarterDeadlineForm(request.POST or None, instance=quarter)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Deadline saved."))
        return redirect("events:settings")
    return render(request, "events/simple_form.html", {
        "form": form, "title": _("Submission deadline for %(q)s") % {"q": quarter.label}})


@manager_required
def email_settings(request):
    site = SiteSettings.load()
    form = EmailSettingsForm(request.POST or None, instance=site)
    if request.method == "POST" and form.is_valid():
        site = form.save()
        if "test" in request.POST:
            if not site.email_ready:
                messages.error(request, _("Turn on “send emails” and enter the email to send from first."))
            elif not request.user.email:
                messages.error(request, _("Add your own email in “My account” to receive the test."))
            else:
                try:
                    emailing.send_to_users([request.user], ("Prueba de correo", "Test email"),
                                           "Si recibe esto, los correos funcionan. ✅",
                                           "If you got this, email is working. ✅", site=site, raise_errors=True)
                    messages.success(request, _("Test email sent to %(email)s.") % {"email": request.user.email})
                except Exception as exc:
                    messages.error(request, _("The email could not be sent: %(error)s") % {"error": exc})
        else:
            messages.success(request, _("Settings saved."))
        return redirect("events:email_settings")
    return render(request, "events/email_settings.html", {"form": form, "site": site})
