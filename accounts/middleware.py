from django.utils import translation


class UserLanguageMiddleware:
    """Logged-in users always see the app in the language saved on their profile."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.language:
            translation.activate(user.language)
            request.LANGUAGE_CODE = user.language
        return self.get_response(request)
