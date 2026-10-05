from django.db import models

from apps.common.models import DireccionBase


class PerfilDireccion(DireccionBase):
    campo_dueno = "perfil"

    perfil = models.ForeignKey("profiles.Perfil", on_delete=models.CASCADE, related_name="direcciones")

    class Meta:
        db_table = "perfiles_direcciones"
        verbose_name = "Dirección del equipo"
        verbose_name_plural = "Direcciones del equipo"
        constraints = DireccionBase.restricciones("perfil")
