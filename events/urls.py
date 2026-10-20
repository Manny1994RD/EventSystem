from django.urls import path

from . import reports, views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("events/", views.event_list, name="list"),
    path("events/new/", views.event_create, name="create"),
    path("events/submit-all/", views.submit_all, name="submit_all"),
    path("events/<int:pk>/", views.event_detail, name="detail"),
    path("events/<int:pk>/edit/", views.event_edit, name="edit"),
    path("events/<int:pk>/delete/", views.event_delete, name="delete"),
    path("events/<int:pk>/submit/", views.event_submit, name="submit"),
    path("events/<int:pk>/withdraw/", views.event_withdraw, name="withdraw"),
    path("events/<int:pk>/review/", views.event_review, name="review"),
    path("events/<int:pk>/change/", views.change_request, name="change_request"),
    path("events/<int:pk>/flyer/", views.flyer_upload, name="flyer_upload"),
    path("events/<int:pk>/flyer/review/", views.flyer_review, name="flyer_review"),
    path("changes/<int:pk>/decide/", views.change_decide, name="change_decide"),
    path("flyers/<int:pk>/file/", views.flyer_file, name="flyer_file"),
    path("review/", views.review_queue, name="review_queue"),
    path("review/flyers/", views.flyer_queue, name="flyer_queue"),
    path("designer/", views.designer_queue, name="designer_queue"),
    path("region/", views.regional, name="regional"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar/day/", views.day_check, name="day_check"),
    path("public/", views.public_calendar, name="public_calendar"),
    path("public/event/<int:pk>/", views.public_event, name="public_event"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/", views.notification_open, name="notification_open"),
    path("reports/", reports.report_page, name="reports"),
    path("reports/excel/", reports.report_excel, name="report_excel"),
    path("reports/pdf/", reports.report_pdf, name="report_pdf"),
    path("settings/", views.settings_home, name="settings"),
    path("settings/email/", views.email_settings, name="email_settings"),
    path("settings/churches/new/", views.church_edit, name="church_new"),
    path("settings/churches/<int:pk>/", views.church_edit, name="church_edit"),
    path("settings/types/new/", views.event_type_edit, name="type_new"),
    path("settings/types/<int:pk>/", views.event_type_edit, name="type_edit"),
    path("settings/quarters/<int:pk>/", views.quarter_edit, name="quarter_edit"),
]
