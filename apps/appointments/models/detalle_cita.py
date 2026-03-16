from django.db import models
from model_utils.models import TimeStampedModel


class DetalleCita(TimeStampedModel):
    cita = models.ForeignKey(
        "appointments.Cita", on_delete=models.CASCADE, related_name="detalles"
    )
    servicio = models.ForeignKey(
        "services.Servicio", on_delete=models.SET_NULL, null=True
    )

    # Snapshot del servicio al momento de agendar
    nombre_servicio = models.CharField(max_length=200)
    precio_servicio = models.DecimalField(max_digits=10, decimal_places=0)
    duracion_estimada_servicio = models.DurationField(blank=True, null=True)

    precio_acordado = models.DecimalField(max_digits=10, decimal_places=0)
    cantidad_servicios = models.PositiveIntegerField(default=1)
    notas_detalle = models.TextField(blank=True, null=True)
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
    )

    class Meta:
        app_label = "appointments"
        db_table = "detalle_cita"
        verbose_name = "Detalle de Cita"
        verbose_name_plural = "Detalles de Citas"
        unique_together = ["cita", "servicio"]

    def __str__(self):
        return f"Detalle {self.pk} - {self.nombre_servicio} - Cita {self.cita.pk}"

    def save(self, *args, **kwargs):
        if self.servicio and not self.nombre_servicio:
            self.nombre_servicio = self.servicio.nombre
        if self.servicio and not self.precio_servicio:
            self.precio_servicio = self.servicio.precio
        if self.servicio and not self.duracion_estimada_servicio:
            self.duracion_estimada_servicio = self.servicio.duracion_estimada
        if not self.precio_acordado:
            self.precio_acordado = self.precio_servicio
        super().save(*args, **kwargs)
