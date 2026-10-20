from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LockoutAuthenticationForm

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html",
                                                authentication_form=LockoutAuthenticationForm,
                                                redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("language/", views.set_language, name="set_language"),
    path("setup/", views.setup, name="setup"),
    path("healthz", views.healthz, name="healthz"),
    path("profile/", views.profile, name="profile"),
    path("users/", views.user_list, name="users"),
    path("users/new/", views.user_edit, name="user_new"),
    path("users/<int:pk>/", views.user_edit, name="user_edit"),
]
