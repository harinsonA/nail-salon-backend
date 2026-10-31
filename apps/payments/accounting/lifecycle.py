from django.utils import timezone

from apps.common.utils.text import user_display_name
from apps.payments.accounting.account import PaymentAccount
from apps.payments.accounting.constants import ZERO
from apps.payments.accounting.header import PaymentHeader
from apps.payments.accounting.ledger import AppointmentLedger
from apps.payments.accounting.rows import PaymentRowFactory
from apps.payments.choices import EstadoDetallePago, EstadoPago
from apps.payments.models import Pago


class AppointmentPaymentService:
    def __init__(self, appointment, user):
        self.appointment = appointment
        self.user = user
        self.header = PaymentHeader(appointment)

    def ledger(self):
        return AppointmentLedger.for_appointment(self.appointment)

    def row_factory(self, moment=None):
        return PaymentRowFactory(self.user, moment or timezone.now())

    def register_advances(self, advances):
        if not advances:
            return None
        payment = Pago(cita=self.appointment)
        factory = self.row_factory()
        rows = [factory.advance(payment, advance) for advance in advances]
        self.header.fill(payment, details=rows)
        payment.save()
        for row in rows:
            row.save()
        return payment

    def sync_advances(self, changes):
        added = [change for change in changes if change["row"] is None]
        payment = self.ledger().payment
        if payment is None:
            return self.register_advances(added)
        for change in changes:
            row = change["row"]
            if row is None:
                continue
            if change["remove"]:
                row.delete()
            else:
                self.update_advance(row, change)
        factory = self.row_factory()
        for change in added:
            factory.advance(payment, change).save()
        self.header.fill(payment).save()
        return payment

    @staticmethod
    def update_advance(row, change):
        values = {
            "monto_pago": change["amount"],
            "metodo_pago": change["method"],
            "referencia_pago": PaymentRowFactory.reference(
                change["method"], change["reference"]
            ),
        }
        if all(getattr(row, name) == value for name, value in values.items()):
            return
        for name, value in values.items():
            setattr(row, name, value)
        row.save()

    def complete(self, amount, method, reference, notes):
        payment = self.ledger().payment or Pago(cita=self.appointment)
        details = list(payment.detalles_pago.all()) if payment.pk else []
        self.header.fill(payment, details=details)
        payment.atendido_por = self.user
        payment.atendido_por_nombre = user_display_name(self.user)
        installment = (
            self.row_factory().installment(payment, amount, method, reference, notes)
            if amount
            else None
        )
        if installment:
            details.append(installment)
        if PaymentAccount(payment, details).is_settled():
            payment.estado_pago = EstadoPago.COMPLETADO
            payment.fecha_pago_completado = timezone.now()
        payment.save()
        if installment:
            installment.save()
        return payment

    def cancel(self, refunds):
        ledger = self.ledger()
        payment = ledger.payment
        if payment is None:
            return None
        factory = self.row_factory()
        for row in ledger.open_advances():
            refund = refunds.get(row.pk)
            if refund:
                factory.refund(row, refund).save()
                row.estado_detalle = EstadoDetallePago.DEVUELTO
            else:
                row.estado_detalle = EstadoDetallePago.RETENIDO
            row.save()
        self.header.fill(payment, cancelled=True)
        if PaymentAccount(payment).paid() > ZERO:
            payment.estado_pago = EstadoPago.COMPLETADO
            payment.fecha_pago_completado = factory.moment
        else:
            payment.estado_pago = EstadoPago.REEMBOLSADO
        payment.save()
        return payment

    def restore(self, restored):
        ledger = self.ledger()
        payment = ledger.payment
        if payment is None:
            return None
        for row in ledger.retained_advances():
            if row.pk in restored:
                row.estado_detalle = EstadoDetallePago.VIGENTE
            else:
                row.estado_detalle = EstadoDetallePago.RETENIDO_DEFINITIVO
            row.save()
        self.header.fill(payment)
        payment.estado_pago = EstadoPago.PENDIENTE
        payment.fecha_pago_completado = None
        payment.save()
        return payment


class InstallmentService:
    def __init__(self, payment, user):
        self.payment = payment
        self.user = user

    def register(self, amount, method, reference, notes, moment):
        PaymentRowFactory(self.user, moment).installment(
            self.payment, amount, method, reference, notes
        ).save()
        if not PaymentAccount(self.payment).is_settled():
            return False
        self.payment.estado_pago = EstadoPago.COMPLETADO
        self.payment.fecha_pago_completado = timezone.now()
        self.payment.save()
        return True
