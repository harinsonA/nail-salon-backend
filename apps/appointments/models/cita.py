from django.db import models
from django.contrib.auth.models import User
from utils.choices import EstadoCita


class Cita(models.Model):
    cita_id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(
        "clients.Cliente", on_delete=models.CASCADE, related_name="citas"
    )
    fecha_hora_cita = models.DateTimeField()
    estado_cita = models.CharField(
        max_length=20, choices=EstadoCita.CHOICES, default=EstadoCita.PENDIENTE
    )
    observaciones = models.TextField(blank=True, null=True)

    # Campos adicionales de gestión
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        app_label = "appointments"
        db_table = "citas"
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["-fecha_hora_cita"]

    def __str__(self):
        return f"Cita {self.cita_id} - {self.cliente.nombre_completo} - {self.fecha_hora_cita.strftime('%d/%m/%Y %H:%M')}"

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
        return self.estado_cita not in [EstadoCita.COMPLETADA, EstadoCita.CANCELADA]
