"""Logo, app icons, web-app manifest and service worker (so people can install the app on their phone)."""

import hashlib
import io
import json

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control

from .models import SiteSettings

ICON_SIZES = (180, 192, 512)


def logo(request):
    site = SiteSettings.load()
    if not site.logo:
        raise Http404
    try:
        resp = FileResponse(site.logo.open("rb"))
    except FileNotFoundError:
        raise Http404
    resp["Cache-Control"] = "public, max-age=604800"
    return resp


def _hex_to_rgb(value):
    value = (value or "#1e3a8a").lstrip("#")
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (30, 58, 138)


def _draw_icon(site, size):
    """The logo on a white rounded square, or a simple white church on the main color."""
    from PIL import Image, ImageDraw, ImageOps

    color = _hex_to_rgb(site.brand_color)
    if site.logo:
        try:
            with site.logo.open("rb") as fh, Image.open(fh) as img:
                img = ImageOps.exif_transpose(img).convert("RGBA")
                canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
                inner = int(size * 0.8)
                img.thumbnail((inner, inner))
                canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
                return canvas.convert("RGB")
        except Exception:
            pass
    img = Image.new("RGB", (size, size), color)
    d = ImageDraw.Draw(img)
    s = size / 24
    w = max(2, int(size * 0.06))
    white = (255, 255, 255)
    # cross
    d.line([(12 * s, 3.5 * s), (12 * s, 8 * s)], fill=white, width=w)
    d.line([(9.8 * s, 5.5 * s), (14.2 * s, 5.5 * s)], fill=white, width=w)
    # roof and walls
    d.line([(6 * s, 13 * s), (12 * s, 9 * s), (18 * s, 13 * s)], fill=white, width=w, joint="curve")
    d.line([(6.5 * s, 12.6 * s), (6.5 * s, 20 * s), (17.5 * s, 20 * s), (17.5 * s, 12.6 * s)], fill=white, width=w)
    # door
    d.rounded_rectangle([(10.5 * s, 15.5 * s), (13.5 * s, 20 * s)], radius=int(1.4 * s), outline=white, width=w)
    return img


@cache_control(public=True, max_age=86400)
def app_icon(request, size):
    if size not in ICON_SIZES:
        raise Http404
    site = SiteSettings.load()
    key = hashlib.sha1(f"{site.logo.name}|{site.brand_color}|{size}".encode()).hexdigest()[:16]
    cache_dir = settings.DATA_DIR / "cache" / "icons"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.png"
    if not path.exists():
        out = io.BytesIO()
        _draw_icon(site, size).save(out, "PNG", optimize=True)
        path.write_bytes(out.getvalue())
    return HttpResponse(path.read_bytes(), content_type="image/png")


@cache_control(public=True, max_age=3600)
def manifest(request):
    site = SiteSettings.load()
    from django.utils.translation import gettext as _

    name = site.app_name or _("Church Events")
    data = {
        "name": name,
        "short_name": name[:20],
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": site.brand_color or "#1e3a8a",
        "theme_color": site.brand_color or "#1e3a8a",
        "lang": "es",
        "icons": [
            {"src": reverse("app_icon", args=[192]), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": reverse("app_icon", args=[512]), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": reverse("app_icon", args=[512]), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


def service_worker(request):
    js = render(request, "sw.js", {
        "offline_url": reverse("offline"),
        "assets": [static("css/app.css"), static("js/app.js")],
    }, content_type="application/javascript")
    js["Cache-Control"] = "no-cache"
    js["Service-Worker-Allowed"] = "/"
    return js


def offline(request):
    return render(request, "offline.html")
