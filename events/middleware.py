from .models import SiteSettings


class SettingsCacheMiddleware:
    """Start every request with fresh settings, so a change made by an admin shows up right away."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        SiteSettings.clear_cache()
        try:
            return self.get_response(request)
        finally:
            SiteSettings.clear_cache()
