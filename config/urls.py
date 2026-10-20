from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Eventos — Tech Admin"

urlpatterns = [
    path("tech-admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("events.urls")),
]
