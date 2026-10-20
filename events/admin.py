from django.contrib import admin

from .models import Activity, ChangeRequest, Church, Event, EventType, Flyer, Notification, Quarter, SiteSettings


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "church", "date", "status", "flyer_status", "is_late", "limit_override")
    list_filter = ("status", "flyer_status", "church", "quarter")
    search_fields = ("title", "location")


for model in (Church, EventType, Quarter, SiteSettings, Flyer, ChangeRequest, Activity, Notification):
    admin.site.register(model)
