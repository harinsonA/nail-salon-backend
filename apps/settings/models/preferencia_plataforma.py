from django.db import models

from apps.settings.preferences.constants import Scope
from apps.settings.preferences.models import Preference


class PreferenciaPlataformaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(scope=Scope.PLATAFORMA)


class PreferenciaPlataforma(Preference):
    objects = PreferenciaPlataformaManager()

    class Meta:
        proxy = True
        app_label = "settings"
        default_permissions = ("view", "change")
        verbose_name = "App móvil"
        verbose_name_plural = "App móvil"
