from django.db.models import Exists, OuterRef

from apps.payments.accounting.constants import RESERVATION_TYPES
from apps.payments.accounting.detail import PaymentDetail
from apps.payments.choices import EstadoDetallePago, TipoDetallePago
from apps.payments.models import DetallePago, Pago


class AppointmentLedger:
    def __init__(self, payment):
        self.payment = payment

    @classmethod
    def for_appointment(cls, appointment):
        if appointment is None or appointment.pk is None:
            return cls(None)
        return cls(Pago.objects.filter(cita=appointment).first())

    def rows_of(self, kinds):
        if self.payment is None:
            return []
        refunds = DetallePago.objects.filter(detalle_devuelto=OuterRef("pk"))
        return list(
            self.payment.detalles_pago.filter(tipo_detalle__in=kinds)
            .annotate(has_refunds=Exists(refunds))
            .order_by("fecha_pago", "pk")
        )

    @staticmethod
    def open_rows(rows):
        return [
            row
            for row in rows
            if not row.has_refunds
            and PaymentDetail.status(row) == EstadoDetallePago.VIGENTE
        ]

    def advances(self):
        return self.rows_of([TipoDetallePago.ANTICIPO])

    def open_advances(self):
        return self.open_rows(self.advances())

    def open_reservation(self):
        return next(iter(self.open_rows(self.rows_of(RESERVATION_TYPES))), None)

    def retained_advances(self):
        return [
            row
            for row in self.advances()
            if row.estado_detalle == EstadoDetallePago.RETENIDO
        ]
