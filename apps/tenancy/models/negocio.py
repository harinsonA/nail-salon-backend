from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django_tenants.models import TenantMixin
from django_tenants.utils import get_public_schema_name
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.utils.utils import CommonCleaner


FAILED_STATUS_KEY = "fallido"
FAILED_STATUS_LABEL = "Falló"


def validar_zona_horaria(valor):
    resultado = CommonCleaner.clean_time_zone_field(valor)
    if resultado.is_err():
        raise ValidationError(resultado.value)


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

    @property
    def preparation_failed(self):
        return self.estado == self.Estado.PREPARANDO and bool(self.error_preparacion)

    @property
    def status_key(self):
        return FAILED_STATUS_KEY if self.preparation_failed else self.estado

    @property
    def status_label(self):
        return FAILED_STATUS_LABEL if self.preparation_failed else self.get_estado_display()

    def clean(self):
        super().clean()
        if self.schema_name and self.schema_name != get_public_schema_name():
            resultado = CommonCleaner.clean_schema_field(self.schema_name)
            if resultado.is_err():
                raise ValidationError(resultado.value)
