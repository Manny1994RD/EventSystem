from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from events import branding, ical

admin.site.site_header = "Eventos — Tech Admin"

urlpatterns = [
    # Outside the "events" namespace: browsers expect these at fixed addresses.
    path("manifest.webmanifest", branding.manifest, name="manifest"),
    path("sw.js", branding.service_worker, name="service_worker"),
    path("offline/", branding.offline, name="offline"),
    path("calendar.ics", ical.calendar_feed, name="calendar_feed"),
    path("brand/logo", branding.logo, name="brand_logo"),
    path("brand/icon-<int:size>.png", branding.app_icon, name="app_icon"),
    path("", include("accounts.urls")),
    path("", include("events.urls")),
]
if settings.TECH_ADMIN_ENABLED:
    urlpatterns.insert(0, path("tech-admin/", admin.site.urls))
