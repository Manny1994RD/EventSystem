from django.urls import reverse
from django.utils.translation import gettext as _

from .models import SiteSettings


def brand(request):
    site = SiteSettings.load()
    return {
        "brand_name": site.app_name or _("Church Events"),
        "brand_color": site.brand_color or "#1e3a8a",
        "brand_logo": reverse("brand_logo") + f"?v={site.logo.name.split('/')[-1]}" if site.logo else "",
    }


from django.utils.translation import gettext as _


def nav(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "unread_count": user.notifications.filter(is_read=False).count(),
        "day_check_text": {
            "free": _("This day is free in the region. 👍"),
            "some": _("{n} of {limit} spots taken that day:"),
            "full": _("This day is FULL in the region. Please pick another date (or ask for an exception)."),
        },
    }
