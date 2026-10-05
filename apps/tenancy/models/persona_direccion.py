from django.db import models

from apps.common.models import DireccionBase


class PersonaDireccion(DireccionBase):
    campo_dueno = "persona"

    persona = models.ForeignKey("tenancy.Persona", on_delete=models.CASCADE, related_name="direcciones")

    class Meta:
        db_table = "personas_direcciones"
        verbose_name = "Dirección de persona"
        verbose_name_plural = "Direcciones de personas"
        constraints = DireccionBase.restricciones("persona")
