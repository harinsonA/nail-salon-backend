import datetime
from django.db import models
from model_utils.models import TimeStampedModel, SoftDeletableModel
from simple_history.models import HistoricalRecords


class ServicioActivoManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                estado=self.model.EstadoChoices.ACTIVO,
                is_removed=False,
            )
        )


class ServicioInactivoManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                estado=self.model.EstadoChoices.INACTIVO,
                is_removed=False,
            )
        )


class Servicio(TimeStampedModel, SoftDeletableModel):
    class EstadoChoices(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ACTIVO,
        db_index=True,
    )
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    duracion_estimada = models.DurationField(
        blank=True, null=True, default=datetime.timedelta(minutes=30)
    )

    # Auditoría completa (crítico para cambios de precio)
    history = HistoricalRecords(inherit=True)

    # Managers
    objects = models.Manager()  # Manager por defecto (todos)
    activos = ServicioActivoManager()  # Solo activos
    inactivos = ServicioInactivoManager()  # Solo inactivos

    class Meta:
        app_label = "services"
        db_table = "servicios"
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def id(self):
        """Alias para pk para compatibilidad con tests y API estándar"""
        return self.pk

    @property
    def duracion_en_minutos(self):
        """Retorna la duración en minutos"""
        if self.duracion_estimada:
            return int(self.duracion_estimada.total_seconds() / 60)
        return 0

    def get_precio_formateado(self):
        """Retorna el precio formateado como string"""
        return f"${self.precio:,.0f}"
