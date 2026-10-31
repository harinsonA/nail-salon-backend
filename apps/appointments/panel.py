from django.urls import reverse
from django.utils import timezone

from apps.appointments.access import is_collaborator
from apps.appointments.models import Cita
from apps.common.utils.currency import Money
from apps.common.utils.dates import format_date_time, format_long_date
from apps.common.utils.text import user_display_name
from apps.payments.choices import EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.payments.services.account import PaymentAccount
from apps.payments.services.advances import open_advances, retained_advances

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

METHOD_LABELS = dict(MetodoPago.CHOICES)
REFUND_METHODS = [
    (MetodoPago.EFECTIVO, METHOD_LABELS[MetodoPago.EFECTIVO]),
    (MetodoPago.TRANSFERENCIA, METHOD_LABELS[MetodoPago.TRANSFERENCIA]),
]


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
        rows = []
        subtotal = 0
        discounts = 0
        for detail in self.appointment.detalles.order_by("pk"):
            line_subtotal = detail.precio_servicio * detail.cantidad_servicios
            subtotal += line_subtotal
            discounts += detail.descuento
            rows.append(
                {
                    "name": detail.nombre_servicio,
                    "quantity": detail.cantidad_servicios,
                    "price": Money.format(detail.precio_servicio),
                    "discount": Money.format(-detail.descuento) if detail.descuento else "",
                    "total": Money.format(line_subtotal - detail.descuento),
                }
            )
        return rows, subtotal, discounts

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
        installments = list(
            DetallePago.objects.filter(pago=payment).select_related("registrado_por").order_by("fecha_pago", "pk")
        )
        account = PaymentAccount(payment, installments)
        paid = account.paid()
        pending = account.balance()
        rows = [
            {"label": "Total de la cita", "value": Money.format(payment.monto_total_cita)},
            {"label": "Pagado", "value": Money.format(paid)},
        ]
        if pending:
            rows.append({"label": "Saldo pendiente", "value": Money.format(pending), "debt": True})
        first = installments[0] if installments else None
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
            "installments": [
                {
                    "when": format_date_time(item.fecha_pago),
                    "method": METHOD_LABELS.get(item.metodo_pago, item.metodo_pago),
                    "by": user_display_name(item.registrado_por).split(" ")[0] if item.registrado_por else "—",
                    "amount": Money.format(item.monto_pago),
                }
                for item in installments
            ],
        }

    @staticmethod
    def cancelled_payment(payment):
        account = PaymentAccount(payment) if payment else None
        if not account or not account.details:
            return {"rows": [{"label": "Estado", "value": "Sin pago: la cita fue cancelada"}]}
        refunded = sum(
            (item.monto_pago for item in account.details if item.tipo_detalle == TipoDetallePago.DEVOLUCION),
            0,
        )
        return {
            "rows": [
                {"label": "Estado", "value": "Cita cancelada"},
                {"label": "Retenido", "value": Money.format(account.retained())},
                {"label": "Reembolsado", "value": Money.format(refunded)},
            ]
        }

    def cancel_advances(self, payment):
        if self.mode["key"] != "cancel" or not payment:
            return None
        rows = open_advances(payment)
        if not rows:
            return None
        return {
            "locked": is_collaborator(self.viewer),
            "config": {
                "rows": self.advance_rows(rows),
                "refundMethods": REFUND_METHODS,
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
                "methodLabel": METHOD_LABELS.get(row.metodo_pago, row.metodo_pago),
                "date": format_date_time(row.fecha_pago),
            }
            for row in rows
        ]

    def restore_advances(self, payment, total):
        if self.mode["key"] != "restore" or not payment:
            return None
        rows = retained_advances(payment)
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
        services, subtotal, discounts = self.services()
        total = subtotal - discounts
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
