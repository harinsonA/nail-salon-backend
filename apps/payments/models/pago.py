from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel
from simple_history.models import HistoricalRecords

from apps.common.utils.currency import Money
from apps.payments.choices import EstadoPago


class PagoManager(models.Manager):
    """Manager que excluye pagos eliminados"""

    def get_queryset(self):
        return super().get_queryset().filter(is_removed=False)


class Pago(TimeStampedModel, SoftDeletableModel):
    """
    Modelo de cabecera para control de pagos de una cita.
    Registra el monto total a pagar y el estado consolidado de los pagos.
    Los pagos individuales (abonos) se registran en DetallePago.
    """

    cita = models.OneToOneField(
        "appointments.Cita",
        on_delete=models.CASCADE,
        related_name="pago",
    )
    monto_total_cita = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Monto total que debe pagarse por la cita",
    )
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPago.CHOICES,
        default=EstadoPago.PENDIENTE,
        db_index=True,
    )
    cliente_nombre = models.CharField(
        max_length=200,
        help_text="Nombre del cliente al momento de crear el pago (snapshot)",
    )
    fecha_cita = models.DateTimeField(
        help_text="Fecha y hora de la cita (snapshot)",
    )
    fecha_pago_completado = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Fecha y hora en que el pago se completó totalmente",
    )
    descuento_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Descuento total aplicado al pago",
    )
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pagos_atendidos",
    )
    atendido_por_nombre = models.CharField(max_length=150, blank=True, null=True)

    # Auditoría histórica
    history = HistoricalRecords(inherit=True)

    # Managers
    objects = PagoManager()  # Manager por defecto (excluye eliminados)
    all_objects = models.Manager()  # Manager que incluye eliminados

    class Meta:
        app_label = "payments"
        db_table = "pagos"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-created"]

    def __str__(self):
        return f"Pago {self.pk} - Cita {self.cita.pk} - {Money.format(self.monto_total_cita)}"
