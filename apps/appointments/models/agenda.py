from django.conf import settings
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel
from simple_history.models import HistoricalRecords


class CitaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_removed=False)


class Cita(TimeStampedModel, SoftDeletableModel):
    class EstadoChoices(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        COMPLETADA = "completada", "Completada"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey(
        "clients.Cliente", on_delete=models.CASCADE, related_name="citas"
    )
    fecha_agenda = models.DateField()
    hora_agenda = models.TimeField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
        db_index=True,
    )
    observaciones = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="citas_creadas",
    )
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="citas_asignadas",
    )

    # Auditoría completa (crítico para cambios de estado)
    history = HistoricalRecords(inherit=True)

    # Managers
    objects = CitaManager()  # Manager por defecto (excluye eliminados)
    all_objects = models.Manager()  # Manager que incluye eliminados

    class Meta:
        app_label = "appointments"
        db_table = "citas"
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["-fecha_agenda"]

    def __str__(self):
        return f"Cita {self.pk} - {self.fecha_agenda.strftime('%d/%m/%Y')}"

    @property
    def duracion_total(self):
        """Calcula la duración total estimada de la cita"""
        total_segundos = sum(
            detalle.duracion_estimada_servicio.total_seconds()
            * detalle.cantidad_servicios
            for detalle in self.detalles.all()
            if detalle.duracion_estimada_servicio
        )
        return total_segundos / 60  # Retorna en minutos

    def puede_ser_modificada(self):
        """Verifica si la cita puede ser modificada"""
        return self.estado not in [
            Cita.EstadoChoices.COMPLETADA,
            Cita.EstadoChoices.CANCELADA,
        ]
