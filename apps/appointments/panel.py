from django.urls import reverse
from django.utils import timezone

from apps.appointments.access import is_collaborator
from apps.appointments.models import Cita
from apps.common.utils.currency import Money
from apps.common.utils.dates import format_date_time, format_long_date
from apps.common.utils.text import user_display_name
from apps.payments.accounting import (
    AppointmentLedger,
    AppointmentPaymentSummary,
    PaymentAccount,
    PaymentLabels,
    ServiceLines,
)
from apps.payments.choices import EstadoPago, MetodoPago
from apps.payments.models import Pago

"""========================================================================="""
# region ........ Constants


OVERDUE_STATUS = "vencida"

STATUS_LABELS = {
    Cita.EstadoChoices.PENDIENTE: "Pendiente",
    Cita.EstadoChoices.COMPLETADA: "Completada",
    Cita.EstadoChoices.CANCELADA: "Cancelada",
    OVERDUE_STATUS: "Pendiente sin cerrar",
}

PANEL_MODES = {
    "detail": {"variant": "primary", "icon": "calendar_month.svg", "title": "Detalle de cita"},
    "cancel": {
        "variant": "secondary",
        "light": True,
        "icon": "cancel.svg",
        "title": "Cancelar cita",
        "confirm_label": "Cancelar cita",
    },
    "restore": {
        "variant": "success",
        "light": True,
        "icon": "refresh.svg",
        "title": "Restaurar cita",
        "confirm_label": "Restaurar cita",
    },
    "delete": {
        "variant": "danger-subtle",
        "icon": "warning-text-danger.svg",
        "title": "Eliminar cita",
        "title_class": "text-color-destructive",
        "confirm_label": "Eliminar cita",
        "button": "danger",
    },
}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def is_unclosed(status, day, hour, now):
    return status == Cita.EstadoChoices.PENDIENTE and (day < now.date() or (day == now.date() and hour < now.time()))


def person_name(person, viewer):
    if not person:
        return ""
    name = user_display_name(person)
    return f"{name} (tú)" if viewer and person.pk == viewer.pk else name


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Builders


class AppointmentPanel:
    def __init__(self, appointment, viewer, mode="detail"):
        self.appointment = appointment
        self.viewer = viewer
        self.mode = {"key": mode, **PANEL_MODES[mode]}

    def client_name(self):
        client = self.appointment.cliente
        return f"{client.nombre} {client.apellido or ''}".strip()

    def status(self):
        appointment = self.appointment
        unclosed = is_unclosed(appointment.estado, appointment.fecha_agenda, appointment.hora_agenda, timezone.localtime())
        key = OVERDUE_STATUS if unclosed else appointment.estado
        return {"key": key, "label": STATUS_LABELS[key]}

    def payment_record(self):
        try:
            payment = self.appointment.pago
        except Pago.DoesNotExist:
            return None
        return None if payment.is_removed else payment

    def services(self):
        rows = [
            {
                "name": detail.nombre_servicio,
                "quantity": detail.cantidad_servicios,
                "price": Money.format(detail.precio_servicio),
                "discount": Money.format(-detail.descuento) if detail.descuento else "",
                "total": Money.format(detail.precio_acordado),
            }
            for detail in self.appointment.detalles.order_by("pk")
        ]
        return (rows, *ServiceLines.amounts(self.appointment))

    def team(self, payment):
        appointment = self.appointment
        if appointment.estado == Cita.EstadoChoices.COMPLETADA and payment and payment.atendido_por_id:
            attended = person_name(payment.atendido_por, self.viewer) or payment.atendido_por_nombre
            return {"label": "Atendió", "name": attended}
        return {"label": "Asignada a", "name": person_name(appointment.asignado_a, self.viewer) or "Sin asignar"}

    def payment(self, payment, total):
        status = self.appointment.estado
        if status == Cita.EstadoChoices.CANCELADA:
            return self.cancelled_payment(payment)
        if status == Cita.EstadoChoices.PENDIENTE or not payment:
            rows = [
                {"label": "Estado", "value": "Se registra al completar la cita"},
                {"label": "Monto estimado", "value": Money.format(total)},
            ]
            advance = PaymentAccount(payment).credit() if payment else 0
            if advance:
                rows += [
                    {"label": "Anticipo", "value": Money.format(advance)},
                    {"label": "Restante por pagar", "value": Money.format(max(0, total - advance))},
                ]
            return {"rows": rows}
        summary = AppointmentPaymentSummary.for_payment(payment)
        pending = summary.pending()
        rows = [
            {"label": "Total de la cita", "value": Money.format(summary.total())},
            {"label": "Pagado", "value": Money.format(summary.paid())},
        ]
        if pending:
            rows.append({"label": "Saldo pendiente", "value": Money.format(pending), "debt": True})
        payments = summary.payments()
        first = payments[0] if payments else None
        can_pay = pending and payment.estado_pago == EstadoPago.PENDIENTE
        return {
            "pay_url": reverse("agenda_payment_modal", args=[payment.pk]) if can_pay else "",
            "badge": {"label": "Pago incompleto", "debt": True} if pending else {"label": "Pagado", "debt": False},
            "rows": rows,
            "first": {
                "name": person_name(first.registrado_por, self.viewer) or "—",
                "when": format_date_time(first.fecha_pago),
            }
            if first
            else None,
            "payments": summary.rows(),
        }

    @staticmethod
    def cancelled_payment(payment):
        account = PaymentAccount(payment) if payment else None
        if not account or not account.details:
            return {"rows": [{"label": "Estado", "value": "Sin pago: la cita fue cancelada"}]}
        return {
            "rows": [
                {"label": "Estado", "value": "Cita cancelada"},
                {"label": "Retenido", "value": Money.format(account.retained())},
                {"label": "Reembolsado", "value": Money.format(account.refunded_total())},
            ]
        }

    def cancel_advances(self, payment):
        if self.mode["key"] != "cancel" or not payment:
            return None
        rows = AppointmentLedger(payment).open_advances()
        if not rows:
            return None
        return {
            "locked": is_collaborator(self.viewer),
            "config": {
                "rows": self.advance_rows(rows),
                "refundMethods": PaymentLabels.refund_choices(),
                "cash": MetodoPago.EFECTIVO,
                "transfer": MetodoPago.TRANSFERENCIA,
                "referenceMaxLength": 100,
            },
        }

    @staticmethod
    def advance_rows(rows):
        return [
            {
                "id": row.pk,
                "amount": int(row.monto_pago),
                "method": row.metodo_pago,
                "methodLabel": PaymentLabels.method(row.metodo_pago),
                "date": format_date_time(row.fecha_pago),
            }
            for row in rows
        ]

    def restore_advances(self, payment, total):
        if self.mode["key"] != "restore" or not payment:
            return None
        rows = AppointmentLedger(payment).retained_advances()
        if not rows:
            return None
        return {
            "locked": is_collaborator(self.viewer),
            "config": {
                "rows": self.advance_rows(rows),
                "servicesTotal": int(total),
                "prepaid": int(PaymentAccount(payment).credit()),
            },
        }

    def context(self):
        appointment = self.appointment
        payment = self.payment_record()
        services, subtotal, discounts, total = self.services()
        return {
            "mode": self.mode,
            "client_name": self.client_name(),
            "phone": appointment.cliente.telefono or "Sin teléfono",
            "date_label": format_long_date(appointment.fecha_agenda),
            "time_label": appointment.hora_agenda.strftime("%H:%M"),
            "status": self.status(),
            "team": self.team(payment),
            "services": services,
            "subtotal": Money.format(subtotal),
            "discounts": Money.format(-discounts) if discounts else Money.format(0),
            "total": Money.format(total),
            "payment": self.payment(payment, total),
            "cancel_advances": self.cancel_advances(payment),
            "restore_advances": self.restore_advances(payment, total),
            "notes": appointment.observaciones,
            "created_by": person_name(appointment.creado_por, self.viewer),
            "created_at": format_date_time(appointment.created),
        }


# endregion
"""========================================================================="""
