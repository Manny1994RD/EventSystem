"""First-time setup: until the first account exists, every page leads to a screen that creates it.

To make sure only the person who installed the app can do this, the screen asks for a one-time code.
The code is written to the data folder (setup-code.txt) and to the app's log.
"""

import secrets

from django.conf import settings
from django.shortcuts import redirect

from .models import User

CODE_FILE = "setup-code.txt"
_users_exist = False


def users_exist():
    global _users_exist
    if not _users_exist:
        _users_exist = User.objects.exists()
    return _users_exist


def setup_code(create=True):
    path = settings.DATA_DIR / CODE_FILE
    if path.exists():
        return path.read_text().strip()
    if not create:
        return ""
    code = "-".join(secrets.token_hex(2).upper() for _ in range(3))
    path.write_text(code + "\n")
    return code


def finish_setup():
    global _users_exist
    _users_exist = True
    (settings.DATA_DIR / CODE_FILE).unlink(missing_ok=True)


class FirstRunMiddleware:
    ALLOWED_PREFIXES = ("/setup/", "/static/", "/healthz", "/language/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(self.ALLOWED_PREFIXES) and not users_exist():
            return redirect("setup")
        return self.get_response(request)
