from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from django.contrib.auth import login
from django.http import HttpResponse

from . import setup as first_run
from .forms import FirstAdminForm, ProfileForm, UserForm
from .models import Role, User


def manager_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.user.can_manage:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(wrapper)


@require_POST
def set_language(request):
    lang = request.POST.get("language")
    if lang not in ("es", "en"):
        lang = "es"
    nxt = request.POST.get("next") or "/"
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    if request.user.is_authenticated:
        request.user.language = lang
        request.user.save(update_fields=["language"])
    translation.activate(lang)
    response = redirect(nxt)
    response.set_cookie("django_language", lang, max_age=365 * 24 * 3600, samesite="Lax")
    return response


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user, prefix="p")
    pw_form = PasswordChangeForm(request.user, request.POST or None, prefix="pw")
    if request.method == "POST":
        if "save_profile" in request.POST and form.is_valid():
            form.save()
            messages.success(request, _("Saved."))
            return redirect("profile")
        if "save_password" in request.POST and pw_form.is_valid():
            pw_form.save()
            update_session_auth_hash(request, pw_form.user)
            messages.success(request, _("Your password was changed."))
            return redirect("profile")
    if "save_password" not in request.POST:
        pw_form = PasswordChangeForm(request.user, prefix="pw")
    return render(request, "accounts/profile.html", {"form": form, "pw_form": pw_form})


@manager_required
def user_list(request):
    users = User.objects.select_related("church").order_by("-is_active", "church__name", "first_name")
    return render(request, "accounts/user_list.html", {"users": users})


@manager_required
def user_edit(request, pk=None):
    target = get_object_or_404(User, pk=pk) if pk else None
    if target and target.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    form = UserForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        if target and target.pk == request.user.pk and not form.cleaned_data["is_active"]:
            messages.error(request, _("You can't turn off your own account."))
        else:
            form.save()
            messages.success(request, _("User saved."))
            return redirect("users")
    return render(request, "accounts/user_form.html", {"form": form, "target": target})


def setup(request):
    """Create the first admin account (only while the app has no accounts)."""
    if first_run.users_exist():
        return redirect("login")
    form = FirstAdminForm(request.POST or None, expected_code=first_run.setup_code())
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_superuser(
            username=form.cleaned_data["username"], password=form.cleaned_data["password1"],
            first_name=form.cleaned_data["first_name"], role=Role.TECH_ADMIN, is_app_admin=True,
            language=translation.get_language() or "es",
        )
        first_run.finish_setup()
        login(request, user)
        messages.success(request, _("Welcome! Next, add the churches' users in “Users”."))
        return redirect("users")
    return render(request, "accounts/setup.html", {"form": form})


def healthz(request):
    """Used by Docker / ZimaOS to see that the app is up."""
    User.objects.exists()
    return HttpResponse("ok", content_type="text/plain")
