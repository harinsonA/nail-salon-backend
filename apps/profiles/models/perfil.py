from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.utils.countries.constants import Country


class Perfil(TimeStampedModel):
    class Rol(models.TextChoices):
        PROPIETARIO = "propietario", "Propietario"
        ENCARGADO = "encargado", "Encargado"
        COLABORADOR = "colaborador", "Colaborador"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.COLABORADOR)
    debe_cambiar_clave = models.BooleanField(default=True)
    pais = models.CharField(max_length=2, choices=Country.choices, null=True, blank=True)
    tipo_identificador_nacional = models.CharField(max_length=20, null=True, blank=True)
    identificador_nacional = models.CharField(max_length=20, null=True, blank=True)

    history = HistorialRecords()

    class Meta:
        db_table = "perfiles"
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"
        constraints = [
            models.UniqueConstraint(
                fields=["rol"],
                condition=models.Q(rol="propietario"),
                name="perfiles_un_propietario",
            ),
        ]

    def __str__(self):
        return f"{self.user} ({self.get_rol_display()})"
