from zoneinfo import available_timezones

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django_tenants.models import TenantMixin
from django_tenants.utils import get_public_schema_name
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.tenancy.subdominios import validar_esquema


def validar_zona_horaria(valor):
    if valor not in available_timezones():
        raise ValidationError("«%(valor)s» no es una zona horaria válida.", params={"valor": valor})


class Negocio(TenantMixin, TimeStampedModel):
    class Estado(models.TextChoices):
        PREPARANDO = "preparando", "Preparando"
        ACTIVO = "activo", "Activo"
        MOROSO = "moroso", "Moroso"
        PAUSADO = "pausado", "Pausado"
        CANCELADO = "cancelado", "Cancelado"

    nombre = models.CharField(max_length=150)
    titular = models.ForeignKey(
        "tenancy.Persona",
        on_delete=models.PROTECT,
        null=True,
        related_name="negocios_como_titular",
    )
    rubro = models.ForeignKey(
        "tenancy.Rubro",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="negocios",
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PREPARANDO,
        db_index=True,
    )
    estado_desde = MonitorField(monitor="estado")
    zona_horaria = models.CharField(
        max_length=50,
        default="America/Santiago",
        validators=[validar_zona_horaria],
    )
    error_preparacion = models.TextField(blank=True, null=True)
    notas_internas = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="negocios_creados",
    )

    history = HistorialRecords()

    auto_create_schema = False
    auto_drop_schema = False

    class Meta:
        db_table = "negocios"
        verbose_name = "Negocio"
        verbose_name_plural = "Negocios"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(titular__isnull=False) | models.Q(schema_name=get_public_schema_name()),
                name="negocios_titular_obligatorio",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        if self.schema_name and self.schema_name != get_public_schema_name():
            validar_esquema(self.schema_name)
