from django.db.models import Exists, OuterRef

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

    def advances(self):
        if self.payment is None:
            return []
        refunds = DetallePago.objects.filter(detalle_devuelto=OuterRef("pk"))
        return list(
            self.payment.detalles_pago.filter(tipo_detalle=TipoDetallePago.ANTICIPO)
            .annotate(has_refunds=Exists(refunds))
            .order_by("fecha_pago", "pk")
        )

    def open_advances(self):
        return [
            row
            for row in self.advances()
            if not row.has_refunds
            and PaymentDetail.status(row) == EstadoDetallePago.VIGENTE
        ]

    def retained_advances(self):
        return [
            row
            for row in self.advances()
            if row.estado_detalle == EstadoDetallePago.RETENIDO
        ]
