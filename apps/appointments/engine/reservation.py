from apps.common.utils.dates import format_date_time
from apps.payments.choices import TipoDetallePago
from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
    get_preferences,
)


class AppointmentReservation:
    DISCOUNTS_LABEL = "Descuenta del total"
    SEPARATE_LABEL = "No descuenta del total"

    def __init__(self, ledger, creating):
        self.creating = creating
        settings = get_preferences(
            [
                RESERVATION_ENABLED.key,
                RESERVATION_DISCOUNTS_TOTAL.key,
                RESERVATION_AMOUNT.key,
                RESERVATION_PAYMENT_METHOD.key,
            ]
        )
        self.saved = ledger.open_reservation()
        self.enabled = (
            settings[RESERVATION_ENABLED.key] is True
            and settings[RESERVATION_AMOUNT.key] > 0
        )
        self.settings = settings

    @property
    def available(self):
        return bool(self.saved) or self.enabled

    def amount(self):
        if self.saved:
            return int(self.saved.monto_pago)
        return self.settings[RESERVATION_AMOUNT.key]

    def discounts(self):
        if self.saved:
            return self.saved.tipo_detalle == TipoDetallePago.RESERVA_DESCONTABLE
        return self.settings[RESERVATION_DISCOUNTS_TOTAL.key] is True

    def kind(self):
        if self.discounts():
            return TipoDetallePago.RESERVA_DESCONTABLE
        return TipoDetallePago.RESERVA

    def method(self):
        if self.saved:
            return self.saved.metodo_pago
        return self.settings[RESERVATION_PAYMENT_METHOD.key]

    def mode_label(self):
        return self.DISCOUNTS_LABEL if self.discounts() else self.SEPARATE_LABEL

    def starts_on(self):
        return bool(self.saved) or self.creating

    def config(self, can_change_saved):
        if not self.available:
            return None
        saved = self.saved
        return {
            "amount": self.amount(),
            "discounts": self.discounts(),
            "modeLabel": self.mode_label(),
            "on": self.starts_on(),
            "method": self.method(),
            "reference": (saved.referencia_pago or "") if saved else "",
            "date": format_date_time(saved.fecha_pago) if saved else "",
            "saved": bool(saved),
            "locked": bool(saved) and not can_change_saved,
        }
