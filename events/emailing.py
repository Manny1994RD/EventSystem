"""Sending email with the account an admin entered in Settings. Does nothing while email is off."""

import logging
import threading

from django.conf import settings as django_settings
from django.core.mail import EmailMessage, get_connection
from django.urls import reverse

from .models import SiteSettings

log = logging.getLogger(__name__)

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def connection(site):
    if django_settings.EMAIL_BACKEND != SMTP_BACKEND:
        # Tests (and local development) use Django's configured backend.
        return get_connection()
    return get_connection(
        SMTP_BACKEND, host=site.smtp_host, port=site.smtp_port, username=site.smtp_username or site.email_from,
        password=site.smtp_password, use_tls=site.smtp_port == 587, use_ssl=site.smtp_port == 465, timeout=15,
    )


def event_link(site, event):
    if not (site.site_url and event):
        return ""
    return site.site_url.rstrip("/") + reverse("events:detail", args=[event.pk])


def send_to_users(users, subject, text_es, text_en, event=None, site=None, raise_errors=False):
    """Send each person the message in their own language. Returns how many emails were sent."""
    site = site or SiteSettings.load()
    if not site.email_ready:
        return 0
    link = event_link(site, event)
    messages = []
    for user in users:
        if not user.email or not user.is_active:
            continue
        body = text_en if user.language == "en" else text_es
        if link:
            body += f"\n\n{link}"
        body += "\n\n— " + ("Church Events" if user.language == "en" else "Eventos de la Iglesia")
        subj = subject[1] if user.language == "en" else subject[0]
        messages.append(EmailMessage(subj, body, site.email_from, [user.email]))
    if not messages:
        return 0
    try:
        return connection(site).send_messages(messages) or 0
    except Exception:
        if raise_errors:
            raise
        log.exception("Could not send email")
        return 0


def send_in_background(*args, **kwargs):
    """Send without making the person who clicked wait for the email server."""
    if django_settings.EMAIL_BACKEND != SMTP_BACKEND:
        return send_to_users(*args, **kwargs)  # tests: send right away so they can check the outbox
    threading.Thread(target=send_to_users, args=args, kwargs=kwargs, daemon=True).start()
    return None
