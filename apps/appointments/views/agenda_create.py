import json
from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.models.agenda import Cita
from apps.appointments.models.detalle_cita import DetalleCita
from apps.clients.models import Cliente
from apps.common.custom_time_fields import MONTH_NUMBER_TO_NAME
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT2_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.dates import DAY_OF_WEEK_TO_NAME
from apps.common.utils.text import user_display_name
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedAjaxView, ProtectedView
from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de
from apps.services.models import Categoria, Servicio

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
DISCOUNT_INVALID = "El descuento de «{name}» no puede ser negativo ni superar su precio."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def long_date(value):
    weekday = DAY_OF_WEEK_TO_NAME[value.weekday()].lower()
    month = MONTH_NUMBER_TO_NAME[value.month].lower()
    return f"{weekday} {value.day} {month} {value.year}"


def is_collaborator(user):
    return rol_de(user) == Perfil.Rol.COLABORADOR


def assignable_users(user):
    users = User.objects.filter(is_active=True, perfil__isnull=False).order_by("first_name", "last_name", "email")
    return users.filter(pk=user.pk) if is_collaborator(user) else users


class StaffChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return user_display_name(obj)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AppointmentCreateForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=Cliente.activos.order_by("nombre", "apellido"),
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
        widget=forms.DateInput(format=DATE_FORMAT, attrs={"type": "date", "class": FORM_CONTROL_CLASS}),
    )
    time = forms.TimeField(
        label="Hora",
        input_formats=[TIME_FORMAT],
        widget=forms.TimeInput(format=TIME_FORMAT, attrs={"type": "time", "step": "60", "class": FORM_CONTROL_CLASS}),
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

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["assigned_to"].queryset = assignable_users(user)
        if is_collaborator(user):
            self.fields["assigned_to"].disabled = True
            self.fields["assigned_to"].initial = user

    def clean_services(self):
        try:
            lines = json.loads(self.cleaned_data.get("services") or "[]")
        except json.JSONDecodeError as error:
            raise forms.ValidationError(SERVICES_INVALID) from error
        if not isinstance(lines, list) or not all(isinstance(line, dict) for line in lines):
            raise forms.ValidationError(SERVICES_INVALID)
        if not lines:
            raise forms.ValidationError(SERVICES_REQUIRED)
        try:
            ids = [int(line.get("id")) for line in lines]
        except (TypeError, ValueError) as error:
            raise forms.ValidationError(SERVICES_INVALID) from error
        if len(set(ids)) != len(ids):
            raise forms.ValidationError(SERVICE_REPEATED)
        services = Servicio.activos.in_bulk(ids)
        if len(services) != len(ids):
            raise forms.ValidationError(SERVICE_UNAVAILABLE)
        return [self.clean_line(services[service_id], line) for service_id, line in zip(ids, lines)]

    @staticmethod
    def clean_line(service, line):
        try:
            quantity = int(line.get("cantidad", 1))
            discount = int(line.get("descuento", 0))
        except (TypeError, ValueError) as error:
            raise forms.ValidationError(SERVICES_INVALID) from error
        if not 1 <= quantity <= MAX_QUANTITY:
            raise forms.ValidationError(QUANTITY_INVALID.format(name=service.nombre, max=MAX_QUANTITY))
        subtotal = service.precio * quantity
        if not 0 <= discount <= subtotal:
            raise forms.ValidationError(DISCOUNT_INVALID.format(name=service.nombre))
        return {"service": service, "quantity": quantity, "discount": discount, "total": subtotal - discount}

    def clean_assigned_to(self):
        return self.user if is_collaborator(self.user) else self.cleaned_data["assigned_to"]


class BusyHoursFilterForm(forms.Form):
    fecha = forms.DateField(input_formats=[DATE_FORMAT])
    asignada = forms.IntegerField(required=False)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AgendaCreateView(ProtectedView, FormView):
    template_name = "appointments/agenda_create_modal.html"
    form_class = AppointmentCreateForm

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return redirect("calendar")
        return super().get(request, *args, **kwargs)

    def selected_date(self):
        today = timezone.localdate()
        try:
            selected = date.fromisoformat(self.kwargs.get("date", ""))
        except ValueError:
            return today
        return max(selected, today)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def get_initial(self):
        return {**super().get_initial(), "date": self.selected_date(), "assigned_to": self.request.user}

    @staticmethod
    def services_data():
        services = Servicio.activos.select_related("categoria").order_by("nombre")
        return [
            {
                "id": service.pk,
                "nombre": service.nombre,
                "precio": int(service.precio),
                "categoria": service.categoria_id,
                "categoriaNombre": service.categoria.nombre if service.categoria else "Sin categoría",
            }
            for service in services
        ]

    def get_context_data(self, **kwargs):
        categories = Categoria.activos.order_by("nombre").values("pk", "nombre")
        return {
            **super().get_context_data(**kwargs),
            "modal_url": self.request.path,
            "appointment_form_config": {
                "services": self.services_data(),
                "categories": [{"id": category["pk"], "nombre": category["nombre"]} for category in categories],
                "busyUrl": reverse("available_hours_ajax"),
                "currentUser": self.request.user.pk,
                "maxQuantity": MAX_QUANTITY,
            },
        }

    @transaction.atomic
    def create_appointment(self, data):
        appointment = Cita.objects.create(
            cliente=data["client"],
            fecha_agenda=data["date"],
            hora_agenda=data["time"],
            estado=Cita.EstadoChoices.PENDIENTE,
            observaciones=data["observations"] or None,
            creado_por=self.request.user,
            asignado_a=data["assigned_to"],
        )
        DetalleCita.objects.bulk_create(
            DetalleCita(
                cita=appointment,
                servicio=line["service"],
                nombre_servicio=line["service"].nombre,
                precio_servicio=line["service"].precio,
                duracion_estimada_servicio=line["service"].duracion_estimada,
                precio_acordado=line["total"],
                cantidad_servicios=line["quantity"],
                descuento=line["discount"],
            )
            for line in data["services"]
        )
        return appointment

    def form_valid(self, form):
        appointment = self.create_appointment(form.cleaned_data)
        client = f"{appointment.cliente.nombre} {appointment.cliente.apellido or ''}".strip()
        when = f"{long_date(appointment.fecha_agenda)}, {appointment.hora_agenda.strftime(TIME_FORMAT)}"
        return JsonResponse(
            {"message": f"Cita agendada: {client}, {when}.", "fecha": appointment.fecha_agenda.isoformat()}
        )

    def form_invalid(self, form):
        return JsonResponse({"errors": get_errors_to_response(form.errors)}, status=HTTP_400_BAD_REQUEST)


class ServiceDetailsAjax(ProtectedAjaxView, TemplateView):
    def get(self, request, *args, **kwargs):
        service_id = request.GET.get("service_id", None)
        if not service_id:
            return JsonResponse(
                {"message": "El ID del servicio es requerido."},
                status=HTTP_400_BAD_REQUEST,
            )
        service = Servicio.activos.filter(pk=service_id).first()
        if not service:
            return JsonResponse(
                {"error": "Servicios no encontrados"},
                status=HTTP_400_BAD_REQUEST,
            )
        data = {
            "id": service.id,
            "nombre": service.nombre,
            "precio": int(service.precio),
            "duracion_estimada": service.duracion_estimada.total_seconds() // 60,
        }
        return JsonResponse(data)


class AvailableHoursAjax(ProtectedAjaxView, View):
    def get(self, request, *args, **kwargs):
        form = BusyHoursFilterForm(request.GET)
        if not form.is_valid():
            return JsonResponse({"horas": []})
        appointments = Cita.objects.filter(fecha_agenda=form.cleaned_data["fecha"]).exclude(
            estado=Cita.EstadoChoices.CANCELADA
        )
        if is_collaborator(request.user):
            appointments = appointments.filter(asignado_a=request.user)
        assigned = form.cleaned_data["asignada"]
        hours = {}
        for hour, assigned_id in appointments.order_by("hora_agenda").values_list("hora_agenda", "asignado_a_id"):
            key = hour.strftime(TIME_FORMAT)
            item = hours.setdefault(key, {"hora": key, "total": 0, "de_asignada": False})
            item["total"] += 1
            item["de_asignada"] = item["de_asignada"] or (assigned is not None and assigned_id == assigned)
        return JsonResponse({"horas": list(hours.values())})


class ServicesByCategoryAjax(ProtectedAjaxView, TemplateView):
    def get(self, request, *args, **kwargs):
        category_id = request.GET.get("category_id", None)
        if category_id is None:
            return JsonResponse({"results": []})
        if category_id == "":
            queryset = Servicio.activos.filter(categoria__isnull=True)
        else:
            queryset = Servicio.activos.filter(categoria_id=category_id)
        results = [{"id": s.pk, "text": s.nombre} for s in queryset]
        return JsonResponse({"results": results})


# endregion
"""========================================================================="""
