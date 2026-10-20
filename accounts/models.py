from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    CHURCH_LEADER = "church_leader", _("Church Leader")
    CHURCH_REP = "church_rep", _("Church Events Rep")
    REGIONAL_REP = "regional_rep", _("Regional Events Rep")
    OVERSEER = "overseer", _("Overseer")
    DESIGNER = "designer", _("Graphic Designer")
    TECH_ADMIN = "tech_admin", _("Tech Admin")


CHURCH_ROLES = {Role.CHURCH_LEADER, Role.CHURCH_REP}
REVIEWER_ROLES = {Role.REGIONAL_REP, Role.OVERSEER}


class User(AbstractUser):
    role = models.CharField(_("role"), max_length=20, choices=Role.choices, default=Role.CHURCH_REP)
    church = models.ForeignKey(
        "events.Church", verbose_name=_("church"), null=True, blank=True,
        on_delete=models.PROTECT, related_name="users",
    )
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    language = models.CharField(_("language"), max_length=5, choices=[("es", "Español"), ("en", "English")], default="es")
    is_app_admin = models.BooleanField(
        _("can manage users and settings"), default=False,
        help_text=_("Lets this person add users and churches and change settings."),
    )

    class Meta:
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_church_user(self):
        return self.role in CHURCH_ROLES

    @property
    def is_reviewer(self):
        """Regional Events Rep or Overseer: approve events, move dates, override the daily limit."""
        return self.role in REVIEWER_ROLES

    @property
    def can_review_flyers(self):
        """Either the Overseer or the Regional Events Rep can review flyers."""
        return self.role in REVIEWER_ROLES

    @property
    def is_designer(self):
        return self.role == Role.DESIGNER

    @property
    def can_manage(self):
        return self.is_superuser or self.is_app_admin or self.role == Role.TECH_ADMIN

    @property
    def sees_all_churches(self):
        return self.is_reviewer or self.is_designer or self.can_manage
