import hashlib
import secrets

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
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


class LockoutAuthenticationForm(AuthenticationForm):
    """Normal login, but after too many wrong passwords the account is locked for a while."""

    locked_message = ""

    error_messages = {
        **AuthenticationForm.error_messages,
        "locked": _("Too many wrong attempts. Please wait %(minutes)s minutes and try again, "
                    "or ask your administrator."),
    }

    @staticmethod
    def _key(username):
        return "login-fails:" + hashlib.sha256((username or "").strip().lower().encode()).hexdigest()

    def clean(self):
        username = self.cleaned_data.get("username")
        key = self._key(username)
        if cache.get(key, 0) >= settings.LOGIN_MAX_ATTEMPTS:
            self.locked_message = self.error_messages["locked"] % {"minutes": settings.LOGIN_LOCKOUT_SECONDS // 60}
            raise forms.ValidationError(
                self.error_messages["locked"], code="locked",
                params={"minutes": settings.LOGIN_LOCKOUT_SECONDS // 60},
            )
        try:
            data = super().clean()
        except forms.ValidationError:
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, settings.LOGIN_LOCKOUT_SECONDS)
            raise
        cache.delete(key)
        return data


class FirstAdminForm(forms.Form):
    code = forms.CharField(label=_("setup code"), help_text=_(
        "You'll find it in the file setup-code.txt in the app's data folder, or in the app's log."))
    first_name = forms.CharField(label=_("your name"))
    username = forms.CharField(label=_("username (to log in)"), max_length=150)
    password1 = forms.CharField(label=_("password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("password again"), widget=forms.PasswordInput)

    def __init__(self, *args, expected_code="", **kwargs):
        super().__init__(*args, **kwargs)
        self.expected_code = expected_code

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper().replace(" ", "")
        if not self.expected_code or not secrets.compare_digest(code, self.expected_code):
            raise forms.ValidationError(_("That code is not right."))
        return code

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("That username is taken."))
        return username

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password1") != data.get("password2"):
            self.add_error("password2", _("The two passwords are different."))
        elif data.get("password1"):
            try:
                validate_password(data["password1"])
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return data
