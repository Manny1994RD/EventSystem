import os

from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from . import images
from .models import ChangeRequest, Church, Event, EventReport, EventType, Quarter, SiteSettings

ALLOWED_FLYER_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)


class TimeInput(forms.TimeInput):
    input_type = "time"

    def __init__(self, **kwargs):
        super().__init__(format="%H:%M", **kwargs)


class EventForm(forms.ModelForm):
    church = forms.ModelChoiceField(queryset=Church.objects.filter(is_active=True), label=_("church"))

    class Meta:
        model = Event
        fields = [
            "church", "title", "event_type", "date", "start_time", "end_time", "location", "description",
            "contact_name", "contact_phone", "expected_attendance", "needs_support", "support_notes",
        ]
        widgets = {
            "date": DateInput(attrs={"data-day-check": "1"}),
            "start_time": TimeInput(),
            "end_time": TimeInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["event_type"].queryset = EventType.objects.filter(is_active=True)
        if user is not None and not user.is_reviewer:
            # Church users always create events for their own church.
            del self.fields["church"]

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date < timezone.localdate() and (self.instance.pk is None or self.instance.date != date):
            raise forms.ValidationError(_("This date has already passed."))
        return date

    def clean(self):
        data = super().clean()
        start, end = data.get("start_time"), data.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", _("The end time must be after the start time."))
        if data.get("needs_support") and not data.get("support_notes"):
            self.add_error("support_notes", _("Tell the other churches what help you need."))
        return data


class FlyerUploadForm(forms.Form):
    file = forms.FileField(label=_("Flyer (picture or PDF)"))

    def clean_file(self):
        f = self.cleaned_data["file"]
        if os.path.splitext(f.name)[1].lower() not in ALLOWED_FLYER_EXT:
            raise forms.ValidationError(_("Please upload a picture (JPG, PNG) or a PDF."))
        if f.size > settings.MAX_FLYER_MB * 1024 * 1024:
            raise forms.ValidationError(_("The file is too big (max %(mb)s MB).") % {"mb": settings.MAX_FLYER_MB})
        if images.is_image_name(f.name) and not images.check_image(f):
            raise forms.ValidationError(_("This picture could not be opened. Please try another file."))
        return f


class ChangeRequestForm(forms.ModelForm):
    class Meta:
        model = ChangeRequest
        fields = ["cancel", "new_date", "new_start_time", "new_end_time", "new_location", "reason"]
        widgets = {
            "new_date": DateInput(),
            "new_start_time": TimeInput(),
            "new_end_time": TimeInput(),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        data = super().clean()
        if not data.get("cancel") and not any(
            data.get(f) for f in ("new_date", "new_start_time", "new_end_time", "new_location")
        ):
            raise forms.ValidationError(_("Choose what you want to change, or tick “cancel this event”."))
        if data.get("new_date") and data["new_date"] < timezone.localdate():
            self.add_error("new_date", _("This date has already passed."))
        return data


class ChurchForm(forms.ModelForm):
    class Meta:
        model = Church
        fields = ["name", "color", "is_active"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class EventTypeForm(forms.ModelForm):
    class Meta:
        model = EventType
        fields = ["name_es", "name_en", "full_report", "is_active"]


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "max_events_per_day", "flyer_target_days", "flyer_final_days",
            "submission_days_before_quarter", "auto_approve_designer_flyers",
        ]

    def clean(self):
        data = super().clean()
        if data.get("max_events_per_day") is not None and data["max_events_per_day"] < 1:
            self.add_error("max_events_per_day", _("Must be at least 1."))
        if (data.get("flyer_target_days") or 0) < (data.get("flyer_final_days") or 0):
            self.add_error("flyer_final_days", _("The final deadline must be the same as or closer to the event than the due date."))
        return data


class QuarterDeadlineForm(forms.ModelForm):
    class Meta:
        model = Quarter
        fields = ["submission_deadline"]
        widgets = {"submission_deadline": DateInput()}


class ReportFilterForm(forms.Form):
    quarter = forms.ModelChoiceField(queryset=Quarter.objects.all(), label=_("Quarter"), required=False)
    church = forms.ModelChoiceField(queryset=Church.objects.all(), label=_("church"), required=False,
                                    empty_label=_("All churches"))
    event_type = forms.ModelChoiceField(queryset=EventType.objects.all(), label=_("type of event"), required=False,
                                        empty_label=_("All types"))
    status = forms.ChoiceField(label=_("Status"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import EventStatus

        self.fields["status"].choices = [("", _("All (except drafts)"))] + [
            c for c in EventStatus.choices if c[0] != EventStatus.DRAFT
        ]
        self.fields["quarter"].label_from_instance = lambda q: q.label


class EmailSettingsForm(forms.ModelForm):
    smtp_password = forms.CharField(
        label=_("email password"), required=False, widget=forms.PasswordInput(render_value=False),
        help_text=_("For Gmail, use an “app password”, not the normal password. Leave empty to keep the saved one."),
    )

    class Meta:
        model = SiteSettings
        fields = ["email_enabled", "email_from", "smtp_username", "smtp_password", "smtp_host", "smtp_port",
                  "site_url", "email_reminders", "email_notifications"]

    def clean(self):
        data = super().clean()
        if data.get("email_enabled") and not data.get("email_from"):
            self.add_error("email_from", _("Enter the email to send from before turning email on."))
        return data

    def save(self, commit=True):
        site = super().save(commit=False)
        if not self.cleaned_data.get("smtp_password"):
            site.smtp_password = SiteSettings.objects.get(pk=site.pk).smtp_password
        if commit:
            site.save()
        return site


MAX_REPORT_PHOTOS = 12
PHOTO_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


class MultiplePhotoInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplePhotoField(forms.FileField):
    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data]
        return [single(data, initial)] if data else []


FULL_REPORT_FIELDS = ("members_supporting", "fruits", "bible_studies")


class EventReportForm(forms.ModelForm):
    photos = MultiplePhotoField(
        label=_("Photos"), required=False,
        widget=MultiplePhotoInput(attrs={"multiple": True, "accept": "image/*"}),
    )

    class Meta:
        model = EventReport
        fields = ["members_attended", "supporters_attended", "supporting_churches", "members_supporting", "fruits",
                  "bible_studies", "invites", "cost", "fragrance"]
        widgets = {
            "supporting_churches": forms.CheckboxSelectMultiple,
            "fragrance": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = self.instance.event
        self.fields["photos"].help_text = (_("You can pick several photos at once (up to %(n)s in total).")
                                           % {"n": MAX_REPORT_PHOTOS})
        self.fields["supporting_churches"].queryset = Church.objects.filter(is_active=True).exclude(pk=event.church_id)
        if not event.event_type.full_report:
            # Blood drives, cleanups, etc. only count attendance, invites and cost.
            for name in FULL_REPORT_FIELDS:
                del self.fields[name]
        for name in ("members_attended", "supporters_attended", *FULL_REPORT_FIELDS, "invites", "cost"):
            if name not in self.fields:
                continue
            self.fields[name].widget.attrs.update({"inputmode": "decimal" if name == "cost" else "numeric",
                                                   "min": 0})

    def clean_photos(self):
        files = self.cleaned_data.get("photos") or []
        existing = self.instance.photos.count() if self.instance.pk else 0
        if existing + len(files) > MAX_REPORT_PHOTOS:
            raise forms.ValidationError(_("Too many photos (max %(n)s).") % {"n": MAX_REPORT_PHOTOS})
        for f in files:
            if os.path.splitext(f.name)[1].lower() not in PHOTO_EXT:
                raise forms.ValidationError(_("“%(name)s” is not a photo.") % {"name": f.name})
            if f.size > settings.MAX_FLYER_MB * 1024 * 1024:
                raise forms.ValidationError(_("“%(name)s” is too big (max %(mb)s MB).")
                                            % {"name": f.name, "mb": settings.MAX_FLYER_MB})
            if not images.check_image(f):
                raise forms.ValidationError(_("“%(name)s” is not a photo.") % {"name": f.name})
        return files


class LookForm(forms.ModelForm):
    remove_logo = forms.BooleanField(label=_("remove the logo"), required=False)

    class Meta:
        model = SiteSettings
        fields = ["app_name", "logo", "brand_color"]
        widgets = {"brand_color": forms.TextInput(attrs={"type": "color"}),
                   "logo": forms.FileInput(attrs={"accept": "image/*"})}

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        if f and hasattr(f, "content_type"):
            if not images.is_image_name(f.name) or not images.check_image(f):
                raise forms.ValidationError(_("Please upload a picture (JPG, PNG) or a PDF."))
            if f.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_("The file is too big (max %(mb)s MB).") % {"mb": 5})
        return f

    def save(self, commit=True):
        site = super().save(commit=False)
        if self.cleaned_data.get("remove_logo"):
            site.logo = ""
        if commit:
            site.save()
        return site
