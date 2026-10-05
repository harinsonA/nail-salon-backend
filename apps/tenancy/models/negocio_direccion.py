from django.db import models

from apps.common.models import DireccionBase


class NegocioDireccion(DireccionBase):
    campo_dueno = "negocio"

    negocio = models.ForeignKey("tenancy.Negocio", on_delete=models.CASCADE, related_name="direcciones")

    class Meta:
        db_table = "negocios_direcciones"
        verbose_name = "Dirección de negocio"
        verbose_name_plural = "Direcciones de negocios"
        constraints = DireccionBase.restricciones("negocio")
