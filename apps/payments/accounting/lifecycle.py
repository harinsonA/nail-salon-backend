from django.utils import timezone

from apps.common.utils.text import user_display_name
from apps.payments.accounting.account import PaymentAccount
from apps.payments.accounting.constants import ZERO, ReservationAction
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

    def save_payments(self, advances, reservation=None):
        reservation = reservation or {}
        payment = self.ledger().payment
        added = [change for change in advances if change.get("row") is None]
        creates_reservation = reservation.get("action") == ReservationAction.CREATE
        if payment is None and not added and not creates_reservation:
            return None
        if payment is not None:
            self.change_saved(advances, reservation)
        payment = payment or Pago(cita=self.appointment)
        factory = self.row_factory()
        rows = [factory.advance(payment, change) for change in added]
        if creates_reservation:
            rows.insert(0, factory.reservation(payment, reservation))
        if payment.pk:
            for row in rows:
                row.save()
            self.header.fill(payment).save()
            return payment
        self.header.fill(payment, details=rows)
        payment.save()
        for row in rows:
            row.save()
        return payment

    def change_saved(self, advances, reservation):
        for change in advances:
            row = change.get("row")
            if row is None:
                continue
            if change["remove"]:
                row.delete()
            else:
                self.update_row(row, change)
        action = reservation.get("action")
        if action == ReservationAction.REMOVE:
            reservation["row"].delete()
        elif action == ReservationAction.UPDATE:
            self.update_row(reservation["row"], reservation)

    @staticmethod
    def update_row(row, change):
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
        for row in ledger.open_prepaid():
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
        for row in ledger.retained_prepaid():
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
