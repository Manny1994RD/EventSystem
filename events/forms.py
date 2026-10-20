import os

from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import ChangeRequest, Church, Event, EventType, Quarter, SiteSettings

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
        fields = ["name_es", "name_en", "is_active"]


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
