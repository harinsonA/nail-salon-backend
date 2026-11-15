from django.db import transaction

from apps.appointments.engine.errors import AppointmentRuleError
from apps.appointments.engine.messages import (
    AMOUNT_TOO_HIGH,
    BALANCE_PAYMENT_LABEL,
    COMPLETE_NOT_PENDING,
    FULL_PAYMENT_LABEL,
    NOTHING_TO_CHARGE,
    PREPAID_TOO_HIGH,
    SETTLED_HINT,
    SETTLED_SUBJECTS,
)
from apps.appointments.engine.reservation import AppointmentReservation
from apps.appointments.models import Cita
from apps.common.utils.currency import Money
from apps.common.utils.utils import CommonCleaner
from apps.payments.accounting import (
    ZERO,
    AppointmentLedger,
    AppointmentPaymentService,
    AppointmentPaymentSummary,
    PaymentAccount,
    PaymentHeader,
)
from apps.payments.choices import TipoDetallePago


class AppointmentCompletion:
    FIELD = "down_payment"
    AMOUNT_NAME = "monto abonado"

    def __init__(self, appointment):
        self.appointment = appointment
        self.payment = AppointmentLedger.for_appointment(appointment).payment
        self.services_total = PaymentHeader(appointment).services_total()
        self.summary = AppointmentPaymentSummary(self.payment) if self.payment else None
        self.prepaid = PaymentAccount(self.payment).credit() if self.payment else ZERO
        self.remaining = max(ZERO, self.services_total - self.prepaid)

    @classmethod
    def error(cls, message):
        return AppointmentRuleError(message, cls.FIELD)

    def full_payment_label(self):
        return BALANCE_PAYMENT_LABEL if self.prepaid else FULL_PAYMENT_LABEL

    def clean_amount(self, full_payment, amount):
        if self.prepaid > self.services_total:
            raise self.error(
                PREPAID_TOO_HIGH.format(
                    paid=Money.format(self.prepaid),
                    total=Money.format(self.services_total),
                )
            )
        if not self.remaining:
            return 0
        if full_payment:
            return amount
        result = CommonCleaner.clean_amount_field(self.AMOUNT_NAME, amount)
        if result.is_err():
            raise self.error(result.err_value)
        amount = result.ok_value
        if amount >= self.remaining:
            raise self.error(
                AMOUNT_TOO_HIGH.format(
                    total=Money.format(self.remaining), label=self.full_payment_label()
                )
            )
        return amount

    def amount_paid_now(self, full_payment, amount):
        if not self.remaining:
            return ZERO
        if full_payment:
            return self.remaining
        return amount or ZERO

    def credit_parts(self):
        return self.summary.credit_parts() if self.summary else []

    def settled_hint(self):
        labels = tuple(label for label, _ in self.credit_parts())
        if not labels:
            return NOTHING_TO_CHARGE
        return SETTLED_HINT.format(subject=SETTLED_SUBJECTS[labels])

    def advance_part(self):
        return dict(self.credit_parts()).get("Anticipo", ZERO)

    def reservation_card(self):
        row = AppointmentLedger(self.payment).open_reservation() if self.payment else None
        if row is None:
            return None
        discounts = row.tipo_detalle == TipoDetallePago.RESERVA_DESCONTABLE
        return {
            "label": (
                AppointmentReservation.DISCOUNTS_LABEL
                if discounts
                else AppointmentReservation.SEPARATE_LABEL
            ),
            "amount": Money.format(-row.monto_pago if discounts else row.monto_pago),
            "discounts": discounts,
        }

    @transaction.atomic
    def complete(self, user, amount, method, reference, notes):
        if self.appointment.estado != Cita.EstadoChoices.PENDIENTE:
            raise AppointmentRuleError(COMPLETE_NOT_PENDING)
        payment = AppointmentPaymentService(self.appointment, user).complete(
            amount=amount, method=method, reference=reference, notes=notes
        )
        self.appointment.estado = Cita.EstadoChoices.COMPLETADA
        self.appointment.save()
        return payment
