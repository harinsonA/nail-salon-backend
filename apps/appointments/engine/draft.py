from apps.appointments.engine.advances import AdvanceChanges
from apps.appointments.engine.assignment import AppointmentAssignment
from apps.appointments.engine.errors import AppointmentRuleError
from apps.appointments.engine.prepaid_limit import PrepaidLimit
from apps.appointments.engine.reservation import AppointmentReservation
from apps.appointments.engine.reservation_change import ReservationChange
from apps.appointments.engine.services import AppointmentServices
from apps.payments.accounting import AppointmentLedger


class AppointmentDraft:
    def __init__(self, user, appointment=None):
        self.user = user
        self.appointment = appointment
        self.assignment = AppointmentAssignment(user)
        ledger = AppointmentLedger.for_appointment(appointment)
        self.payment = ledger.payment
        self.reservation = AppointmentReservation(ledger, creating=appointment is None)
        self.services = AppointmentServices.for_appointment(appointment)
        self.advances = AdvanceChanges(
            ledger.open_advances(), self.assignment.can_change_saved
        )
        self.reservation_change = ReservationChange(
            self.reservation, self.assignment.can_change_saved
        )
        self.limit = PrepaidLimit(self.payment, self.advances.saved, self.reservation)

    @property
    def can_change_saved(self):
        return self.assignment.can_change_saved

    def sections(self):
        return (
            (AppointmentServices.FIELD, self.services.clean),
            (AdvanceChanges.FIELD, self.advances.clean),
            (ReservationChange.FIELD, self.reservation_change.clean),
        )

    def validate(self, data):
        cleaned = {"assigned_to": self.assignment.resolve(data.get("assigned_to"))}
        errors = {}
        for field, rule in self.sections():
            try:
                cleaned[field] = rule(data.get(field))
            except AppointmentRuleError as error:
                errors[field] = [error.message]
        if not errors:
            error = self.limit.check(
                cleaned[AppointmentServices.FIELD],
                cleaned[AdvanceChanges.FIELD],
                cleaned[ReservationChange.FIELD],
            )
            if error:
                errors[error.field] = [error.message]
        return cleaned, errors
