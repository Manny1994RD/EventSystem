from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from events.models import Church

from .models import CHURCH_ROLES, User


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label=_("password"), required=False, widget=forms.PasswordInput(render_value=False),
        help_text=_("At least 8 characters. Leave empty to keep the current password."),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "role", "church", "phone", "email", "language",
                  "is_app_admin", "is_active"]
        labels = {"first_name": _("first name"), "last_name": _("last name"),
                  "username": _("username (to log in)"), "is_active": _("can log in")}
        help_texts = {"username": _("Simple, no spaces. Example: maria.santiago")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["church"].queryset = Church.objects.filter(is_active=True)
        self.fields["first_name"].required = True
        if self.instance.pk is None:
            self.fields["password"].required = True
            self.fields["password"].help_text = _("At least 8 characters. Give it to the person so they can log in.")

    def clean(self):
        data = super().clean()
        if data.get("role") in CHURCH_ROLES and not data.get("church"):
            self.add_error("church", _("Church Leaders and Church Events Reps must belong to a church."))
        if data.get("password"):
            try:
                validate_password(data["password"], self.instance)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "email", "language"]
        labels = {"first_name": _("first name"), "last_name": _("last name")}
