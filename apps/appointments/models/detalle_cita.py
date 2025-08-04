from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class DetalleCita(models.Model):
    detalle_cita_id = models.AutoField(primary_key=True)
    cita = models.ForeignKey(
        "appointments.Cita", on_delete=models.CASCADE, related_name="detalles"
    )
    servicio = models.ForeignKey("services.Servicio", on_delete=models.CASCADE)
    precio_acordado = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_servicios = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )

    # Campos adicionales
    notas_detalle = models.TextField(blank=True, null=True)
    descuento = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "appointments"
        db_table = "detalle_cita"
        verbose_name = "Detalle de Cita"
        verbose_name_plural = "Detalles de Citas"
        unique_together = ["cita", "servicio"]  # Un servicio por cita

    def __str__(self):
        return f"Detalle {self.detalle_cita_id} - {self.servicio.nombre_servicio} - Cita {self.cita.cita_id}"

    @property
    def subtotal(self):
        """Calcula el subtotal del detalle (precio * cantidad - descuento)"""
        subtotal_bruto = self.precio_acordado * self.cantidad_servicios
        descuento_total = subtotal_bruto * (self.descuento / Decimal("100"))
        return subtotal_bruto - descuento_total

    @property
    def precio_unitario_con_descuento(self):
        """Calcula el precio unitario después del descuento"""
        descuento_decimal = self.descuento / Decimal("100")
        return self.precio_acordado * (Decimal("1") - descuento_decimal)

    def save(self, *args, **kwargs):
        # Si no se especifica un precio acordado, usar el precio del servicio
        if not self.precio_acordado:
            self.precio_acordado = self.servicio.precio
        super().save(*args, **kwargs)
