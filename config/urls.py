from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Eventos — Tech Admin"

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("events.urls")),
]
if settings.TECH_ADMIN_ENABLED:
    urlpatterns.insert(0, path("tech-admin/", admin.site.urls))
