from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class Cita(TimeStampedModel):
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

    # Auditoría completa (crítico para cambios de estado)
    history = HistoricalRecords()

    class Meta:
        app_label = "appointments"
        db_table = "citas"
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["-fecha_agenda"]

    def __str__(self):
        return f"Cita {self.pk} - {self.fecha_agenda.strftime('%d/%m/%Y')}"

    @property
    def monto_total(self):
        """Calcula el monto total de la cita basado en los detalles"""
        return sum(detalle.subtotal for detalle in self.detalles.all())

    @property
    def duracion_total(self):
        """Calcula la duración total estimada de la cita"""
        total_segundos = sum(
            detalle.servicio.duracion_estimada.total_seconds()
            * detalle.cantidad_servicios
            for detalle in self.detalles.all()
        )
        return total_segundos / 60  # Retorna en minutos

    def puede_ser_modificada(self):
        """Verifica si la cita puede ser modificada"""
        return self.estado not in [
            Cita.EstadoChoices.COMPLETADA,
            Cita.EstadoChoices.CANCELADA,
        ]
