from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AppUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "church", "is_app_admin", "is_active")
    list_filter = ("role", "church", "is_active", "is_app_admin")
    fieldsets = UserAdmin.fieldsets + (("Church app", {"fields": ("role", "church", "phone", "language", "is_app_admin")}),)
