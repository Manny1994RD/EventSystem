from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name, extra_class=""):
    """An icon from the sprite in templates/_icons.html, e.g. {% icon "calendar" %}."""
    cls = f"icon {extra_class}".strip()
    return format_html('<svg class="{}" aria-hidden="true"><use href="#i-{}"></use></svg>', cls, name)
