import json
from functools import cached_property

from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.access import is_collaborator
from apps.appointments.models.detalle_cita import DetalleCita
from apps.appointments.panel import AppointmentPanel
from apps.clients.models import Cliente
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT2_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.currency import Money
from apps.common.utils.dates import (
    format_date_time,
    format_long_date,
    format_plain_date,
)
from apps.common.utils.text import user_display_name
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.payments.choices import MetodoPago
from apps.payments.services.account import PaymentAccount
from apps.payments.services.advances import appointment_payment, open_advances
from apps.services.models import Categoria, Servicio
from apps.settings.preferences import ADVANCE_MODULE

User = get_user_model()

"""========================================================================="""
# region ........ Constants


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
MAX_QUANTITY = 99
SERVICES_REQUIRED = "Agrega al menos un servicio."
SERVICES_INVALID = "Los servicios enviados no son válidos."
SERVICE_UNAVAILABLE = "Uno de los servicios ya no está disponible."
SERVICE_REPEATED = "Un servicio no puede repetirse en la misma cita."
QUANTITY_INVALID = "La cantidad de «{name}» debe estar entre 1 y {max}."
DISCOUNT_INVALID = (
    "El descuento de «{name}» no puede ser negativo ni superar su precio."
)
NO_CATEGORY = "Sin categoría"
REFERENCE_MAX_LENGTH = 100
PAYMENT_METHODS = {value for value, _ in MetodoPago.CHOICES}
ADVANCES_INVALID = "Los anticipos enviados no son válidos."
ADVANCE_AMOUNT_REQUIRED = "Ingresa el monto de cada anticipo."
ADVANCE_LOCKED_ROLE = (
    "Solo la propietaria o la encargada pueden cambiar anticipos ya registrados."
)
ADVANCES_TOO_HIGH = (
    "Los anticipos suman {paid} y no pueden superar el total de los servicios "
    "({total})."
)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def assignable_users(user, current=None):
    if is_collaborator(user):
        return User.objects.filter(pk=user.pk)
    condition = Q(is_active=True, perfil__isnull=False)
    if current:
        condition |= Q(pk=current.pk)
    return User.objects.filter(condition).order_by("first_name", "last_name", "email")


def selectable_clients(current=None):
    condition = Q(pk__in=Cliente.activos.values("pk"))
    if current:
        condition |= Q(pk=current.pk)
    return Cliente.objects.filter(condition).order_by("nombre", "apellido")


def client_name(client):
    return f"{client.nombre} {client.apellido or ''}".strip()


def category_name(service):
    return service.categoria.nombre if service and service.categoria else NO_CATEGORY


def service_data(service):
    return {
        "id": service.pk,
        "nombre": service.nombre,
        "precio": int(service.precio),
        "categoria": service.categoria_id,
        "categoriaNombre": category_name(service),
    }


def detail_line(detail):
    service = detail.servicio
    return {
        "detalle": detail.pk,
        "service": {
            "id": detail.servicio_id or f"detalle-{detail.pk}",
            "nombre": detail.nombre_servicio,
            "precio": int(detail.precio_servicio),
            "categoria": service.categoria_id if service else None,
            "categoriaNombre": category_name(service),
        },
        "quantity": detail.cantidad_servicios,
        "discount": int(detail.descuento),
    }


def initial_from(appointment):
    return {
        "client": appointment.cliente,
        "assigned_to": appointment.asignado_a,
        "date": appointment.fecha_agenda,
        "time": appointment.hora_agenda,
        "observations": appointment.observaciones or "",
    }


def build_detail(appointment, line):
    service = line["service"]
    return DetalleCita(
        cita=appointment,
        servicio=service,
        nombre_servicio=service.nombre,
        precio_servicio=service.precio,
        duracion_estimada_servicio=service.duracion_estimada,
        precio_acordado=line["total"],
        cantidad_servicios=line["quantity"],
        descuento=line["discount"],
    )


class StaffChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return user_display_name(obj)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AppointmentForm(BSModalForm):
    client = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        label="Cliente",
        empty_label="Selecciona un cliente",
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    assigned_to = StaffChoiceField(
        queryset=User.objects.none(),
        label="Asignada a",
        empty_label=None,
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    date = forms.DateField(
        label="Fecha",
        input_formats=[DATE_FORMAT],
        widget=forms.DateInput(
            format=DATE_FORMAT,
            attrs={"type": "date", "class": FORM_CONTROL_CLASS},
        ),
    )
    time = forms.TimeField(
        label="Hora",
        input_formats=[TIME_FORMAT],
        widget=forms.TimeInput(
            format=TIME_FORMAT,
            attrs={"type": "time", "step": "60", "class": FORM_CONTROL_CLASS},
        ),
    )
    observations = NoteField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
                "placeholder": "Alergias, preferencias, diseño que quiere…",
            }
        ),
    )
    services = forms.CharField(required=False, widget=forms.HiddenInput)
    advances = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, instance=None, allow_advances=False, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        self.instance = instance
        self.allow_advances = allow_advances
        self.can_change_saved = not is_collaborator(user)
        self.payment = appointment_payment(instance)
        self.saved_advances = open_advances(self.payment) if allow_advances else []
        self.details = {}
        if instance:
            self.details = {detail.pk: detail for detail in instance.detalles.all()}
            self.initial = {**initial_from(instance), **self.initial}
        current_client = instance.cliente if instance else None
        current_staff = instance.asignado_a if instance else None
        self.fields["client"].queryset = selectable_clients(current_client)
        self.fields["assigned_to"].queryset = assignable_users(user, current_staff)
        if is_collaborator(user):
            self.fields["assigned_to"].disabled = True
            self.fields["assigned_to"].initial = user

    def parse_lines(self):
        try:
            lines = json.loads(self.cleaned_data.get("services") or "[]")
        except json.JSONDecodeError as error:
            raise forms.ValidationError(SERVICES_INVALID) from error
        if not isinstance(lines, list):
            raise forms.ValidationError(SERVICES_INVALID)
        if not all(isinstance(line, dict) for line in lines):
            raise forms.ValidationError(SERVICES_INVALID)
        if not lines:
            raise forms.ValidationError(SERVICES_REQUIRED)
        return lines

    def resolve(self, lines):
        new_ids = []
        resolved = []
        try:
            for line in lines:
                if line.get("detalle") is not None:
                    detail = self.details.get(int(line["detalle"]))
                    if not detail:
                        raise forms.ValidationError(SERVICES_INVALID)
                    resolved.append((line, detail, detail.servicio))
                else:
                    new_ids.append(int(line.get("id")))
                    resolved.append((line, None, new_ids[-1]))
        except (TypeError, ValueError) as error:
            raise forms.ValidationError(SERVICES_INVALID) from error
        services = Servicio.activos.in_bulk(new_ids)
        if len(services) != len(set(new_ids)):
            raise forms.ValidationError(SERVICE_UNAVAILABLE)
        return [
            (line, detail, service if detail else services[service])
            for line, detail, service in resolved
        ]

    def clean_services(self):
        resolved = self.resolve(self.parse_lines())
        keys = [
            (
                service.pk if service else None,
                detail.pk if detail and not service else None,
            )
            for _, detail, service in resolved
        ]
        if len(set(keys)) != len(keys):
            raise forms.ValidationError(SERVICE_REPEATED)
        return [
            self.clean_line(line, detail, service)
            for line, detail, service in resolved
        ]

    @staticmethod
    def clean_line(line, detail, service):
        name = detail.nombre_servicio if detail else service.nombre
        price = detail.precio_servicio if detail else service.precio
        try:
            quantity = int(line.get("cantidad", 1))
            discount = int(line.get("descuento", 0))
        except (TypeError, ValueError) as error:
            raise forms.ValidationError(SERVICES_INVALID) from error
        if not 1 <= quantity <= MAX_QUANTITY:
            raise forms.ValidationError(
                QUANTITY_INVALID.format(name=name, max=MAX_QUANTITY)
            )
        subtotal = price * quantity
        if not 0 <= discount <= subtotal:
            raise forms.ValidationError(DISCOUNT_INVALID.format(name=name))
        return {
            "detail": detail,
            "service": service,
            "quantity": quantity,
            "discount": discount,
            "total": subtotal - discount,
        }

    def clean_assigned_to(self):
        user = self.request.user
        return user if is_collaborator(user) else self.cleaned_data["assigned_to"]

    def clean_advances(self):
        if not self.allow_advances:
            return []
        try:
            advances = json.loads(self.cleaned_data.get("advances") or "[]")
        except json.JSONDecodeError as error:
            raise forms.ValidationError(ADVANCES_INVALID) from error
        if not isinstance(advances, list):
            raise forms.ValidationError(ADVANCES_INVALID)
        saved = {row.pk: row for row in self.saved_advances}
        changes = [self.clean_advance(advance, saved) for advance in advances]
        touched = [change["row"].pk for change in changes if change["row"]]
        if len(touched) != len(set(touched)):
            raise forms.ValidationError(ADVANCES_INVALID)
        return changes

    def saved_row(self, advance, saved):
        if advance.get("id") is None:
            return None
        try:
            row = saved.get(int(advance["id"]))
        except (TypeError, ValueError) as error:
            raise forms.ValidationError(ADVANCES_INVALID) from error
        if row is None:
            raise forms.ValidationError(ADVANCES_INVALID)
        if not self.can_change_saved:
            raise forms.ValidationError(ADVANCE_LOCKED_ROLE)
        return row

    def clean_advance(self, advance, saved):
        if not isinstance(advance, dict):
            raise forms.ValidationError(ADVANCES_INVALID)
        row = self.saved_row(advance, saved)
        if row and advance.get("quitar") is True:
            return {"row": row, "remove": True, "amount": 0, "method": row.metodo_pago, "reference": ""}
        amount = advance.get("monto")
        method = advance.get("metodo")
        reference = advance.get("referencia") or ""
        if amount in (None, "", 0):
            raise forms.ValidationError(ADVANCE_AMOUNT_REQUIRED)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise forms.ValidationError(ADVANCES_INVALID)
        if method not in PAYMENT_METHODS or not isinstance(reference, str):
            raise forms.ValidationError(ADVANCES_INVALID)
        reference = reference.strip()
        if len(reference) > REFERENCE_MAX_LENGTH:
            raise forms.ValidationError(ADVANCES_INVALID)
        return {"row": row, "remove": False, "amount": amount, "method": method, "reference": reference}

    def paid_after(self, changes):
        touched = {change["row"].pk for change in changes if change["row"]}
        paid = PaymentAccount(self.payment).credit() if self.payment else 0
        paid -= sum(row.monto_pago for row in self.saved_advances if row.pk in touched)
        return paid + sum(change["amount"] for change in changes if not change["remove"])

    def clean(self):
        cleaned_data = super().clean()
        lines = cleaned_data.get("services")
        if not lines or "advances" not in cleaned_data:
            return cleaned_data
        paid = self.paid_after(cleaned_data["advances"])
        total = sum(line["total"] for line in lines)
        if paid > total:
            self.add_error(
                "advances" if self.allow_advances else "services",
                ADVANCES_TOO_HIGH.format(paid=Money.format(paid), total=Money.format(total)),
            )
        return cleaned_data


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class AppointmentFormMixin:
    template_name = "appointments/agenda_create_modal.html"
    form_class = AppointmentForm
    save_label = "Agendar cita"
    success_prefix = "Cita agendada"

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return redirect("calendar")
        return super().get(request, *args, **kwargs)

    def form_title(self):
        return "Nueva cita"

    def initial_lines(self):
        return []

    @cached_property
    def advances_enabled(self):
        return ADVANCE_MODULE.is_enabled()

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "allow_advances": self.advances_enabled}

    @staticmethod
    def advance_rows(form):
        return [
            {
                "id": row.pk,
                "amount": int(row.monto_pago),
                "method": row.metodo_pago,
                "reference": row.referencia_pago or "",
                "date": format_date_time(row.fecha_pago),
            }
            for row in form.saved_advances
        ]

    def get_context_data(self, **kwargs):
        appointment = getattr(self, "object", None)
        context = super().get_context_data(**kwargs)
        form = context["form"]
        services = Servicio.activos.select_related("categoria").order_by("nombre")
        categories = Categoria.activos.order_by("nombre").values("pk", "nombre")
        return {
            **context,
            "modal_url": self.request.path,
            "form_title": self.form_title(),
            "save_label": self.save_label,
            "advances_enabled": self.advances_enabled,
            "appointment_form_config": {
                "services": [service_data(service) for service in services],
                "categories": [
                    {"id": category["pk"], "nombre": category["nombre"]}
                    for category in categories
                ],
                "lines": self.initial_lines(),
                "appointmentId": appointment.pk if appointment else None,
                "busyUrl": reverse("available_hours_ajax"),
                "currentUser": self.request.user.pk,
                "maxQuantity": MAX_QUANTITY,
                "advances": {
                    "enabled": self.advances_enabled,
                    "rows": self.advance_rows(form),
                    "canChangeSaved": form.can_change_saved,
                    "methods": MetodoPago.CHOICES,
                    "cash": MetodoPago.EFECTIVO,
                    "referenceMaxLength": REFERENCE_MAX_LENGTH,
                },
            },
        }

    def success_message(self, appointment):
        day = format_long_date(appointment.fecha_agenda).lower()
        hour = appointment.hora_agenda.strftime(TIME_FORMAT)
        return f"{self.success_prefix}: {client_name(appointment.cliente)}, {day}, {hour}."

    def form_valid(self, form):
        appointment = self.save_appointment(form.cleaned_data)
        return JsonResponse(
            {
                "message": self.success_message(appointment),
                "fecha": appointment.fecha_agenda.isoformat(),
            }
        )

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


class AppointmentPanelMixin:
    template_name = "appointments/agenda_panel.html"
    panel_mode = "detail"

    def get_context_data(self, **kwargs):
        panel = AppointmentPanel(self.object, self.request.user, self.panel_mode)
        return {
            **super().get_context_data(**kwargs),
            **panel.context(),
            "modal_url": self.request.path,
        }


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AgendaBaseModalView(ProtectedView):
    """Base class for agenda modal views that provides common context data"""

    @staticmethod
    def _get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def _get_date_formatted(object_base) -> str:
        return format_plain_date(object_base.fecha_agenda)

    @staticmethod
    def _get_time_formatted(object_base) -> str:
        return object_base.hora_agenda.strftime("%H:%M")

    @staticmethod
    def _get_phone_number(object_base) -> str:
        return object_base.cliente.telefono or "Sin teléfono"

    @staticmethod
    def _get_details(object_base) -> int:
        counts = object_base.detalles.count()
        details = object_base.detalles.values_list(
            "precio_acordado",
            "descuento",
            "cantidad_servicios",
            "precio_servicio",
        )
        service_totals = 0
        detail_totals = 0
        discount_totals = 0
        for detail in details:
            total, discount, quantity, service_price = detail
            detail_totals += total
            discount_totals += discount
            service_totals += service_price * quantity
        return {
            "services_count": counts,
            "detail_totals": detail_totals,
            "discount_totals": discount_totals,
            "service_totals": service_totals,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]

        context.update(
            {
                "appointment_id": object_base.pk,
                "client_full_name": self._get_client_full_name(object_base),
                "date_formatted": self._get_date_formatted(object_base),
                "time_formatted": self._get_time_formatted(object_base),
                "phone_number": self._get_phone_number(object_base),
                **self._get_details(object_base),
            }
        )
        return context


# endregion
"""========================================================================="""
