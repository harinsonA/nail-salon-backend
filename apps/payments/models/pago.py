from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.payments.choices import MetodoPago, EstadoPago


class Pago(models.Model):
    pago_id = models.AutoField(primary_key=True)
    cita = models.ForeignKey(
        "appointments.Cita", on_delete=models.CASCADE, related_name="pagos"
    )
    fecha_pago = models.DateTimeField()
    monto_total = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.CHOICES)
    estado_pago = models.CharField(
        max_length=20, choices=EstadoPago.CHOICES, default=EstadoPago.PENDIENTE
    )

    # Campos adicionales
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    notas_pago = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "payments"
        db_table = "pagos"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha_pago"]

    def __str__(self):
        return f"Pago {self.pago_id} - Cita {self.cita.pk} - ${self.monto_total}"

    @property
    def es_pago_completo(self):
        """Verifica si el pago cubre el monto total de la cita"""
        return self.monto_total >= self.cita.monto_total

    @property
    def monto_formateado(self):
        """Retorna el monto formateado como string"""
        return f"${self.monto_total:,.0f}"

    def marcar_como_pagado(self):
        """Marca el pago como pagado y actualiza el estado de la cita si es necesario"""
        self.estado_pago = EstadoPago.PAGADO
        self.save()

        # Si el pago está completo, actualizar estado de la cita
        if self.es_pago_completo:
            self.cita.estado = "COMPLETADA"
            self.cita.save()
