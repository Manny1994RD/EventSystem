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
