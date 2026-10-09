from django.db import models

from apps.common.models import TelefonoBase


class PersonaTelefono(TelefonoBase):
    campo_dueno = "persona"

    persona = models.ForeignKey("tenancy.Persona", on_delete=models.CASCADE, related_name="telefonos")

    class Meta:
        db_table = "personas_telefonos"
        verbose_name = "Teléfono de persona"
        verbose_name_plural = "Teléfonos de personas"
        constraints = TelefonoBase.restricciones("persona")
