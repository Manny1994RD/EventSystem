import datetime
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _


class Church(models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)
    color = models.CharField(_("calendar color"), max_length=7, default="#2563eb")
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("church")
        verbose_name_plural = _("churches")

    def __str__(self):
        return self.name


class EventType(models.Model):
    name_es = models.CharField(_("name (Spanish)"), max_length=80)
    name_en = models.CharField(_("name (English)"), max_length=80)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["name_es"]
        verbose_name = _("event type")

    def __str__(self):
        return self.name_en if get_language() == "en" else self.name_es


class SiteSettings(models.Model):
    """One row of settings the admins can change without touching code."""

    max_events_per_day = models.PositiveSmallIntegerField(_("maximum events per day (whole region)"), default=2)
    flyer_target_days = models.PositiveSmallIntegerField(_("flyer due (days before event)"), default=14)
    flyer_final_days = models.PositiveSmallIntegerField(_("flyer final deadline (days before event)"), default=7)
    submission_days_before_quarter = models.PositiveSmallIntegerField(
        _("quarter submissions due (days before quarter starts)"), default=14
    )
    auto_approve_designer_flyers = models.BooleanField(
        _("approve the designer's fixed flyer automatically"), default=False,
        help_text=_("If off, the Overseer or Regional Events Rep gives the final OK after the designer uploads the fix."),
    )

    # Email stays off until an admin enters an account to send from and turns it on.
    email_enabled = models.BooleanField(_("send emails"), default=False)
    email_from = models.EmailField(_("send from this email"), blank=True,
                                   help_text=_("For example the Regional Events Rep's email."))
    smtp_host = models.CharField(_("email server"), max_length=100, default="smtp.gmail.com")
    smtp_port = models.PositiveIntegerField(_("email server port"), default=587)
    smtp_username = models.CharField(_("email username"), max_length=150, blank=True,
                                     help_text=_("Usually the same email address."))
    smtp_password = models.CharField(_("email password"), max_length=200, blank=True,
                                     help_text=_("For Gmail, use an “app password”, not the normal password."))
    email_reminders = models.BooleanField(_("send deadline reminders"), default=True,
                                          help_text=_("Quarter deadline and flyer deadline reminders."))
    email_notifications = models.BooleanField(_("also email every notification"), default=False,
                                              help_text=_("Approvals, changes, flyers… (only to people with an email)."))
    site_url = models.URLField(_("app address"), blank=True,
                               help_text=_("Used for links in emails, e.g. https://zima.your-tailnet.ts.net"))

    class Meta:
        verbose_name = _("settings")
        verbose_name_plural = _("settings")

    @property
    def email_ready(self):
        return self.email_enabled and bool(self.email_from and self.smtp_host)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class Quarter(models.Model):
    year = models.PositiveSmallIntegerField()
    number = models.PositiveSmallIntegerField(choices=[(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4")])
    submission_deadline = models.DateField(_("submission deadline"))

    class Meta:
        ordering = ["year", "number"]
        unique_together = [("year", "number")]

    def __str__(self):
        return f"Q{self.number} {self.year}"

    @property
    def start(self):
        return datetime.date(self.year, 3 * (self.number - 1) + 1, 1)

    @property
    def end(self):
        if self.number == 4:
            return datetime.date(self.year, 12, 31)
        return datetime.date(self.year, 3 * self.number + 1, 1) - datetime.timedelta(days=1)

    @property
    def label(self):
        months = {
            "es": ["Ene–Mar", "Abr–Jun", "Jul–Sep", "Oct–Dic"],
            "en": ["Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec"],
        }
        lang = "en" if get_language() == "en" else "es"
        return f"Q{self.number} {self.year} ({months[lang][self.number - 1]})"

    @property
    def is_past_deadline(self):
        return timezone.localdate() > self.submission_deadline

    @property
    def days_to_deadline(self):
        return (self.submission_deadline - timezone.localdate()).days

    @classmethod
    def for_date(cls, date):
        number = (date.month - 1) // 3 + 1
        quarter = cls.objects.filter(year=date.year, number=number).first()
        if quarter is None:
            start = datetime.date(date.year, 3 * (number - 1) + 1, 1)
            days = SiteSettings.load().submission_days_before_quarter
            quarter = cls.objects.create(
                year=date.year, number=number, submission_deadline=start - datetime.timedelta(days=days)
            )
        return quarter

    @classmethod
    def current(cls):
        return cls.for_date(timezone.localdate())

    def next(self):
        return Quarter.for_date(self.end + datetime.timedelta(days=1))

    def previous(self):
        return Quarter.for_date(self.start - datetime.timedelta(days=1))


class EventStatus(models.TextChoices):
    DRAFT = "draft", _("Draft (not sent yet)")
    SUBMITTED = "submitted", _("Waiting for approval")
    CHANGES = "changes", _("Changes requested")
    APPROVED = "approved", _("Approved")
    DECLINED = "declined", _("Declined")
    CANCELLED = "cancelled", _("Cancelled")


# Events in these statuses take up one of the day's spots on the regional calendar.
SLOT_STATUSES = [EventStatus.SUBMITTED, EventStatus.CHANGES, EventStatus.APPROVED]


class FlyerStatus(models.TextChoices):
    NONE = "none", _("No flyer yet")
    PENDING = "pending", _("Waiting for flyer review")
    DESIGNER = "designer", _("With the designer")
    APPROVED = "approved", _("Flyer approved")


class Event(models.Model):
    church = models.ForeignKey(Church, verbose_name=_("church"), on_delete=models.PROTECT, related_name="events")
    quarter = models.ForeignKey(Quarter, on_delete=models.PROTECT, related_name="events")
    title = models.CharField(_("event name"), max_length=150)
    event_type = models.ForeignKey(EventType, verbose_name=_("type of event"), on_delete=models.PROTECT)
    date = models.DateField(_("date"))
    start_time = models.TimeField(_("starts at"))
    end_time = models.TimeField(_("ends at"), null=True, blank=True)
    location = models.CharField(_("place / address"), max_length=255)
    description = models.TextField(_("description"))
    contact_name = models.CharField(_("contact person"), max_length=100)
    contact_phone = models.CharField(_("contact phone"), max_length=30)
    needs_support = models.BooleanField(_("we need help from other churches"), default=False)
    support_notes = models.CharField(_("what help do you need?"), max_length=255, blank=True)
    expected_attendance = models.PositiveIntegerField(_("expected attendance"), null=True, blank=True)

    status = models.CharField(max_length=12, choices=EventStatus.choices, default=EventStatus.DRAFT)
    flyer_status = models.CharField(max_length=12, choices=FlyerStatus.choices, default=FlyerStatus.NONE)
    review_comment = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)

    # A church can ask for an exception when the day is full; a reviewer grants it.
    exception_requested = models.BooleanField(default=False)
    exception_reason = models.CharField(max_length=255, blank=True)
    limit_override = models.BooleanField(default=False)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="events_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.title} ({self.church}, {self.date})"

    def save(self, *args, **kwargs):
        self.quarter = Quarter.for_date(self.date)
        super().save(*args, **kwargs)

    @property
    def is_ready(self):
        return self.status == EventStatus.APPROVED and self.flyer_status == FlyerStatus.APPROVED

    @property
    def flyer_due_date(self):
        return self.date - datetime.timedelta(days=SiteSettings.load().flyer_target_days)

    @property
    def flyer_final_date(self):
        return self.date - datetime.timedelta(days=SiteSettings.load().flyer_final_days)

    @property
    def flyer_alert(self):
        """None, 'due' (past the target date) or 'overdue' (past the final deadline), while no flyer is approved."""
        if self.flyer_status == FlyerStatus.APPROVED or self.status in (EventStatus.CANCELLED, EventStatus.DECLINED):
            return None
        today = timezone.localdate()
        if today > self.flyer_final_date:
            return "overdue"
        if today > self.flyer_due_date:
            return "due"
        return None

    @property
    def latest_flyer(self):
        return self.flyers.order_by("-version").first()

    @property
    def pending_change(self):
        return self.change_requests.filter(status=ChangeRequest.Status.PENDING).first()


def flyer_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"flyers/{instance.event_id}/{uuid.uuid4().hex}{ext}"


class Flyer(models.Model):
    class Source(models.TextChoices):
        CHURCH = "church", _("Church")
        DESIGNER = "designer", _("Graphic Designer")

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="flyers")
    file = models.FileField(upload_to=flyer_path)
    original_name = models.CharField(max_length=255)
    version = models.PositiveSmallIntegerField(default=1)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.CHURCH)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-version"]

    @property
    def is_image(self):
        return os.path.splitext(self.file.name)[1].lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")


class ChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting")
        APPROVED = "approved", _("Approved")
        DECLINED = "declined", _("Declined")

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="change_requests")
    cancel = models.BooleanField(_("cancel this event"), default=False)
    new_date = models.DateField(_("new date"), null=True, blank=True)
    new_start_time = models.TimeField(_("new start time"), null=True, blank=True)
    new_end_time = models.TimeField(_("new end time"), null=True, blank=True)
    new_location = models.CharField(_("new place / address"), max_length=255, blank=True)
    reason = models.TextField(_("why is this change needed?"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]


class Activity(models.Model):
    """History line on an event. Stored in both languages so everyone reads it in theirs."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="activity")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    text_es = models.TextField()
    text_en = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def text(self):
        return self.text_en if get_language() == "en" else self.text_es


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.CASCADE)
    text_es = models.TextField()
    text_en = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def text(self):
        return self.text_en if get_language() == "en" else self.text_es


class ReminderLog(models.Model):
    """Remembers which reminders were already emailed so nobody gets the same one twice."""

    key = models.CharField(max_length=200, unique=True)
    sent_at = models.DateTimeField(auto_now_add=True)
