from apps.appointments.engine.advances import AdvanceChanges
from apps.appointments.engine.reservation_change import ReservationChange
from apps.appointments.engine.services import AppointmentServices
from apps.payments.accounting import ServiceLines
from apps.payments.accounting.constants import ReservationAction


class AppointmentSummary:
    FIELDS = ("subtotal", "discounts", "total", "reservation", "advances", "balance")

    def __init__(self, draft, cleaned):
        self.draft = draft
        self.lines = cleaned[AppointmentServices.FIELD]
        self.advance_changes = cleaned[AdvanceChanges.FIELD]
        self.reservation_change = cleaned[ReservationChange.FIELD]

    def subtotal(self):
        return int(
            sum(ServiceLines.subtotal(line["price"], line["quantity"]) for line in self.lines)
        )

    def discounts(self):
        return int(sum(line["discount"] for line in self.lines))

    def reservation_active(self):
        offer = self.draft.reservation
        if not offer.available:
            return False
        action = self.reservation_change.get("action")
        if action in (ReservationAction.CREATE, ReservationAction.UPDATE):
            return True
        if action == ReservationAction.REMOVE:
            return False
        return bool(offer.saved)

    def reservation(self):
        return int(self.draft.reservation.amount()) if self.reservation_active() else 0

    def reservation_credit(self):
        if not self.reservation_active() or not self.draft.reservation.discounts():
            return 0
        return self.reservation()

    def advances(self):
        changes = {change["row"].pk: change for change in self.advance_changes if change["row"]}
        kept = 0
        for row in self.draft.advances.saved:
            change = changes.get(row.pk)
            if change is None:
                kept += row.monto_pago
            elif not change["remove"]:
                kept += change["amount"]
        added = sum(change["amount"] for change in self.advance_changes if change["row"] is None)
        return int(kept + added)

    def as_dict(self):
        subtotal = self.subtotal()
        discounts = self.discounts()
        total = subtotal - discounts
        advances = self.advances()
        return {
            "subtotal": subtotal,
            "discounts": discounts,
            "total": total,
            "reservation": self.reservation(),
            "advances": advances,
            "balance": max(0, total - self.reservation_credit() - advances),
        }

    def differences(self, sent):
        calculated = self.as_dict()
        return [field for field in self.FIELDS if sent.get(field) != calculated[field]]
