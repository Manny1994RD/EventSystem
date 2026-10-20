"""Small preview copies of flyers and report photos, so pages load quickly on phones."""

import io
import logging
import os

from django.conf import settings
from django.core.files.base import ContentFile

log = logging.getLogger(__name__)

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def is_image_name(name):
    return os.path.splitext(name)[1].lower() in IMAGE_EXT


def check_image(uploaded):
    """True if the upload really is a picture we can open."""
    from PIL import Image

    try:
        pos = uploaded.tell()
        with Image.open(uploaded) as img:
            img.verify()
        uploaded.seek(pos)
        return True
    except Exception:
        return False


def make_preview(fieldfile):
    """Return a JPEG preview (ContentFile) of an image file, or None if it isn't one."""
    from PIL import Image, ImageOps

    if not is_image_name(fieldfile.name):
        return None
    try:
        with fieldfile.open("rb") as fh, Image.open(fh) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((settings.MAX_FLYER_PREVIEW_PX, settings.MAX_FLYER_PREVIEW_PX))
            if img.mode not in ("RGB", "L"):
                background = Image.new("RGB", img.size, "white")
                background.paste(img, mask=img.convert("RGBA").split()[-1])
                img = background
            out = io.BytesIO()
            img.convert("RGB").save(out, "JPEG", quality=82, optimize=True, progressive=True)
    except Exception:
        log.exception("Could not make a preview of %s", fieldfile.name)
        return None
    base = os.path.splitext(os.path.basename(fieldfile.name))[0]
    return ContentFile(out.getvalue(), name=f"{base}-preview.jpg")


def attach_preview(obj):
    """Create and save obj.preview from obj.file (Flyer or ReportPhoto)."""
    preview = make_preview(obj.file)
    if preview is not None:
        obj.preview.save(preview.name, preview, save=True)
