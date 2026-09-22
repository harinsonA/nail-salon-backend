from django.db import models
from simple_history.models import HistoricalRecords

from apps.settings.preferences.constants import Scope


class Preference(models.Model):
    scope = models.CharField(
        max_length=20,
        choices=Scope.CHOICES,
        default=Scope.USER,
        verbose_name="Alcance",
    )
    scope_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Identificador del alcance",
    )
    key = models.CharField(max_length=100, verbose_name="Clave")
    value = models.JSONField(null=True, blank=True, verbose_name="Valor")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        app_label = "settings"
        db_table = "preference"
        verbose_name = "Preferencia"
        verbose_name_plural = "Preferencias"
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "scope_id", "key"],
                name="preference_scope_key_unique",
            )
        ]

    def __str__(self):
        return f"{self.key} ({self.scope})"
