from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.utils.countries.constants import Country


class PerfilPanel(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_panel"
    )
    pais = models.CharField(max_length=2, choices=Country.choices, null=True, blank=True)
    tipo_identificador_nacional = models.CharField(max_length=20, null=True, blank=True)
    identificador_nacional = models.CharField(max_length=20, null=True, blank=True)

    history = HistorialRecords()

    class Meta:
        db_table = "perfiles_panel"
        verbose_name = "Perfil del panel"
        verbose_name_plural = "Perfiles del panel"

    def __str__(self):
        return f"{self.user}"
