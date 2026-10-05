from django.db import models
from django_tenants.models import TenantMixin
from model_utils.models import TimeStampedModel


class Negocio(TenantMixin, TimeStampedModel):
    nombre = models.CharField(max_length=150)

    auto_create_schema = False
    auto_drop_schema = False

    class Meta:
        db_table = "negocios"
        verbose_name = "Negocio"
        verbose_name_plural = "Negocios"

    def __str__(self):
        return self.nombre
