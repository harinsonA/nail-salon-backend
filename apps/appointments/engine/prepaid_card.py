from apps.common.utils.dates import format_date_time
from apps.payments.accounting import PaymentLabels
from apps.payments.accounting.constants import RESERVATION_TYPES
from apps.payments.choices import TipoDetallePago


class PrepaidCard:
    def __init__(self, rows):
        self.rows = rows
        self.has_reservation = any(row.tipo_detalle in RESERVATION_TYPES for row in rows)
        self.has_advances = any(row.tipo_detalle == TipoDetallePago.ANTICIPO for row in rows)

    def pick(self, advances, reservation, both):
        if not self.has_reservation:
            return advances
        return both if self.has_advances else reservation

    def cancel_title(self):
        subject = self.pick("los anticipos", "la reserva", "la reserva y los anticipos")
        return f"¿Qué hacemos con {subject}?"

    def cancel_hint(self):
        return self.pick(
            "Elige qué pasa con cada anticipo. Lo que retengas queda para el negocio y "
            "vuelve a contar como anticipo si después restauras la cita.",
            "Elige qué pasa con la reserva. Si la retienes queda para el negocio y "
            "puede volver a la cita si después la restauras.",
            "Elige qué pasa con cada pago. Lo que retengas queda para el negocio y "
            "puede volver a la cita si después la restauras.",
        )

    def cancel_locked(self):
        subject = self.pick("anticipos", "una reserva pagada", "una reserva pagada y anticipos")
        return (
            f"Esta cita tiene {subject}. Solo la propietaria o la encargada pueden "
            "cancelarla."
        )

    def restore_title(self):
        subject = self.pick(
            "los anticipos retenidos",
            "la reserva retenida",
            "la reserva y los anticipos retenidos",
        )
        return f"¿Restauramos también {subject}?"

    def restore_hint(self):
        return self.pick(
            "Al cancelar, el negocio se quedó con este dinero. Elige cuáles se restauran "
            "junto con la cita; los que no, quedan para el negocio de forma definitiva.",
            "Al cancelar, el negocio se quedó con la reserva. Elige si vuelve a la cita; "
            "si no, queda para el negocio de forma definitiva.",
            "Al cancelar, el negocio se quedó con este dinero. Elige cuáles se restauran "
            "junto con la cita; los que no, quedan para el negocio de forma definitiva.",
        )

    def restore_locked(self):
        subject = self.pick(
            "anticipos retenidos",
            "una reserva retenida",
            "una reserva y anticipos retenidos",
        )
        return (
            f"Esta cita tiene {subject}. Solo la propietaria o la encargada pueden "
            "restaurarla."
        )

    def back_label(self):
        return self.pick("Anticipo restaurado", "Reserva restaurada", "Restaurado")

    def rows_config(self):
        return [
            {
                "id": row.pk,
                "amount": int(row.monto_pago),
                "kind": PaymentLabels.kind(row.tipo_detalle),
                "reservation": row.tipo_detalle in RESERVATION_TYPES,
                "discounts": row.tipo_detalle != TipoDetallePago.RESERVA,
                "method": row.metodo_pago,
                "methodLabel": PaymentLabels.method(row.metodo_pago),
                "date": format_date_time(row.fecha_pago),
            }
            for row in self.rows
        ]
