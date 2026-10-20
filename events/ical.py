"""Calendar subscription feed (iCalendar). Google Calendar, Apple Calendar and Outlook can subscribe to it
and will show the region's approved events, updating by themselves."""

import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from .models import Church, Event, EventStatus, SiteSettings


def absolute_url(request, path):
    """Full https address for links that leave the app (calendar apps, WhatsApp, emails)."""
    if settings.APP_URL:
        return settings.APP_URL + path
    return request.build_absolute_uri(path)


def _escape(text):
    return (str(text).replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n"))


def _fold(line):
    """iCalendar lines must be at most 75 bytes; longer ones continue on the next line after a space."""
    raw = line.encode()
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode()
        if len(current) + len(b) > (75 if not parts else 74):
            parts.append(current.decode())
            current = b""
        current += b
    parts.append(current.decode())
    return "\r\n ".join(parts)


def _utc(date, time):
    tz = ZoneInfo(settings.TIME_ZONE)
    return datetime.datetime.combine(date, time, tzinfo=tz).astimezone(datetime.timezone.utc)


def _stamp(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")


def calendar_feed(request):
    church = Church.objects.filter(pk=request.GET.get("church")).first() if request.GET.get("church") else None
    since = timezone.localdate() - datetime.timedelta(days=90)
    events = Event.objects.filter(status=EventStatus.APPROVED, date__gte=since).select_related("church", "event_type")
    if church:
        events = events.filter(church=church)
    site = SiteSettings.load()
    name = site.app_name or "Eventos de la Iglesia"
    if church:
        name = f"{name} — {church.name}"
    host = request.get_host().split(":")[0]
    now = _stamp(timezone.now())
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Church Events//EventSystem//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
        f"X-WR-TIMEZONE:{settings.TIME_ZONE}",
        # Ask calendar apps to check for changes every few hours.
        "REFRESH-INTERVAL;VALUE=DURATION:PT4H",
        "X-PUBLISHED-TTL:PT4H",
    ]
    for e in events:
        start = _utc(e.date, e.start_time)
        end = _utc(e.date, e.end_time) if e.end_time else start + datetime.timedelta(hours=2)
        link = absolute_url(request, reverse("events:public_event", args=[e.pk]))
        description = f"{e.church} · {e.event_type}\n\n{e.description}\n\n{link}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:event-{e.pk}@{host}",
            f"DTSTAMP:{now}",
            f"LAST-MODIFIED:{_stamp(e.updated_at)}",
            f"DTSTART:{_stamp(start)}",
            f"DTEND:{_stamp(end)}",
            f"SUMMARY:{_escape(e.title)}",
            f"LOCATION:{_escape(e.location)}",
            f"DESCRIPTION:{_escape(description)}",
            f"URL:{link}",
            f"CATEGORIES:{_escape(e.event_type)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(_fold(line) for line in lines) + "\r\n"
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'inline; filename="eventos.ics"'
    resp["Cache-Control"] = "public, max-age=900"
    return resp


def subscribe_links(request, church=None):
    path = reverse("calendar_feed") + (f"?church={church.pk}" if church else "")
    https_url = absolute_url(request, path)
    webcal = "webcal://" + https_url.split("://", 1)[1]
    from urllib.parse import quote

    return {
        "ics_url": https_url,
        "webcal_url": webcal,
        "google_url": "https://calendar.google.com/calendar/render?cid=" + quote(webcal, safe=""),
    }
