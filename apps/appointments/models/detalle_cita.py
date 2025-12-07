from django.db import models
from decimal import Decimal


class DetalleCita(models.Model):
    cita = models.ForeignKey(
        "appointments.Cita", on_delete=models.CASCADE, related_name="detalles"
    )
    servicio = models.ForeignKey("services.Servicio", on_delete=models.CASCADE)
    precio_acordado = models.DecimalField(max_digits=10, decimal_places=0)
    cantidad_servicios = models.PositiveIntegerField(default=1)
    notas_detalle = models.TextField(blank=True, null=True)
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "appointments"
        db_table = "detalle_cita"
        verbose_name = "Detalle de Cita"
        verbose_name_plural = "Detalles de Citas"
        unique_together = ["cita", "servicio"]  # Un servicio por cita

    def __str__(self):
        return f"Detalle {self.pk} - {self.servicio.nombre} - Cita {self.cita.pk}"

    def save(self, *args, **kwargs):
        # Si no se especifica un precio acordado, usar el precio del servicio
        if not self.precio_acordado:
            self.precio_acordado = self.servicio.precio
        super().save(*args, **kwargs)
