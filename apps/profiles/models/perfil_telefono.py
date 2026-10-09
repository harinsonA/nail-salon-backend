from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TelefonoBase

MAXIMO_POR_PERFIL = 2


class PerfilTelefono(TelefonoBase):
    campo_dueno = "perfil"

    perfil = models.ForeignKey("profiles.Perfil", on_delete=models.CASCADE, related_name="telefonos")

    class Meta:
        db_table = "perfiles_telefonos"
        verbose_name = "Teléfono del equipo"
        verbose_name_plural = "Teléfonos del equipo"
        constraints = TelefonoBase.restricciones("perfil")

    def clean(self):
        super().clean()
        if not self.perfil_id:
            return
        otros = PerfilTelefono.objects.filter(perfil_id=self.perfil_id).exclude(pk=self.pk)
        if otros.count() >= MAXIMO_POR_PERFIL:
            raise ValidationError(
                "Cada usuario puede tener como máximo %(maximo)s teléfonos.",
                params={"maximo": MAXIMO_POR_PERFIL},
            )
