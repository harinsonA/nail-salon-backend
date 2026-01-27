from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from model_utils.models import TimeStampedModel
from apps.payments.choices import MetodoPago
from simple_history.models import HistoricalRecords


class DetallePago(TimeStampedModel):
    """
    Modelo de detalle para registrar cada pago/abono individual.
    Cada registro representa una transacción específica (efectivo, tarjeta, etc.).
    NO usa SoftDeletableModel porque los pagos son registros financieros inmutables.
    """

    pago = models.ForeignKey(
        "payments.Pago",
        on_delete=models.CASCADE,
        related_name="detalles_pago",
    )
    fecha_pago = models.DateTimeField(
        help_text="Fecha y hora en que se realizó este pago específico"
    )
    monto_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Monto de este pago/abono específico",
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.CHOICES,
    )
    referencia_pago = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Número de recibo, transacción, cheque, etc.",
    )
    notas_detalle = models.TextField(blank=True, null=True)

    # Auditoría histórica
    history = HistoricalRecords(inherit=True)

    class Meta:
        app_label = "payments"
        db_table = "detalle_pago"
        verbose_name = "Detalle de Pago"
        verbose_name_plural = "Detalles de Pago"
        ordering = ["-fecha_pago"]

    def __str__(self):
        return f"DetallePago {self.pk} - Pago {self.pago.pk} - ${self.monto_pago}"
