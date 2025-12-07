import json

from datetime import date, datetime
from django import forms
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView

from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomMonthField, CustomDateField
from apps.appointments.models.agenda import Cita
from apps.clients.models import Cliente
from apps.services.models import Servicio

"""========================================================================="""
# region ........ Constants

FORM_CONTROL_CLASS = "form-control form-control--custom"
FORM_CONTROL_TEXTAREA_CLASS = f"{FORM_CONTROL_CLASS} form-control--textarea"
FORM_SELECT_CLASS = "form-select form-select--custom"

# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class AgendaFilterForm(forms.Form):
    months = CustomMonthField(
        required=False,
        label="Mes",
    )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class AgendaModalForm(BSModalForm):
    client = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(
            estado=Cliente.EstadoChoices.ACTIVO, is_removed=False
        ),
        required=True,
        label="Cliente",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    service = forms.ModelChoiceField(
        queryset=Servicio.objects.filter(
            estado=Servicio.EstadoChoices.ACTIVO, is_removed=False
        ),
        required=True,
        label="Servicio",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    date_agenda = CustomDateField(
        required=True,
        label="Fecha de la cita",
    )
    time_agenda = forms.TimeField(
        required=True,
        label="Hora de la cita",
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": FORM_CONTROL_CLASS,
                "format": "%H:%M",
            }
        ),
    )
    observations = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
            }
        ),
    )
    discount_amount = forms.IntegerField(
        label="Descuento",
        initial=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "0",
                "placeholder": "1000",
            }
        ),
    )


class AgendaForm(forms.Form):
    """Formulario normal (no modal) para crear citas de agenda"""

    client = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(
            estado=Cliente.EstadoChoices.ACTIVO, is_removed=False
        ),
        required=True,
        label="Cliente",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    service = forms.ModelChoiceField(
        queryset=Servicio.objects.filter(
            estado=Servicio.EstadoChoices.ACTIVO, is_removed=False
        ),
        required=True,
        label="Servicio",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    date_agenda = CustomDateField(
        required=True,
        label="Fecha de la cita",
    )
    time_agenda = forms.TimeField(
        required=True,
        label="Hora de la cita",
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": FORM_CONTROL_CLASS,
                "format": "%H:%M",
            }
        ),
    )
    observations = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
            }
        ),
    )
    quantity = forms.IntegerField(
        label="Cantidad",
        initial=1,
        min_value=1,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "1",
                "placeholder": "1",
            }
        ),
    )
    discount_amount = forms.IntegerField(
        label="Descuento",
        initial=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "0",
                "placeholder": "1000",
            }
        ),
    )


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class AppointmentsView(TemplateView):
    template_name = "appointments/list.html"

    @staticmethod
    def get_initial_month() -> str:
        today = date.today()
        return f"{today.strftime('%B %Y')}".capitalize()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": AgendaFilterForm(
                    initial={"months": self.get_initial_month()}
                ),
                "url_agenda_list": reverse_lazy("agenda_list"),
            }
        )
        return context


class AgendaListView(BaseListViewAjax):
    model = Cita
    filter_form_class = AgendaFilterForm

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.get_context_data())

    def get_context_data(self, **kwargs):
        filter_form_class = AgendaFilterForm(self.request.GET or None)
        is_valid = filter_form_class.is_valid()
        print("\nIS FILTER FORM VALID?:", is_valid, "\n")
        if is_valid:
            print("\nFILTER FORM CLEANED DATA:", filter_form_class.cleaned_data, "\n")
        print("\nFILTERS APPLIED IN AGENDA LIST VIEW AJAX:", self.request.GET, "\n")
        print(self.get_filters())
        return {
            "data": [],
            "recordsTotal": 0,
            "recordsFiltered": 0,
        }


class AgendaCreateModalView(BSModalFormView):
    template_name = "appointments/agenda_modal.html"
    form_class = AgendaModalForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "date_agenda": date.today().strftime("%d/%m/%Y"),
                "time_agenda": datetime.now().strftime("%H:%M"),
            }
        )
        return initial

    def get_success_url(self):
        return reverse_lazy("agenda_list")


class AgendaCreateV2View(FormView):
    template_name = "appointments/agenda_create_v2.html"
    form_class = AgendaForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "date_agenda": date.today().strftime("%d/%m/%Y"),
                "time_agenda": datetime.now().strftime("%H:%M"),
            }
        )
        return initial

    def get_success_url(self):
        return reverse_lazy("agenda_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Crear Nueva Cita",
                "breadcrumb": "Agenda / Crear Cita",
                "cancel_url": reverse_lazy("appointments"),
                "agenda_create_url": reverse_lazy("agenda_create_v2"),
                "service_details_url": reverse_lazy("service_details_ajax"),
                "available_hours_url": reverse_lazy("available_hours_ajax"),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        print("\n\nPOST DATA RECEIVED IN AGENDA CREATE V2 VIEW:", request.POST, "\n\n")
        agendas = request.POST.get("agenda", None)
        print("\n\nagendas:", type(agendas), agendas, "\n\n")
        if not agendas:
            return JsonResponse(
                {"message": "No se recibieron datos de agenda."},
                status=HTTP_400_BAD_REQUEST,
            )
        agendas = json.loads(agendas)

        print("\n\nagendas:", type(agendas), agendas, "\n\n")
        return JsonResponse({"hola": "mundo"})


class ServiceDetailsAjax(TemplateView):
    def get(self, request, *args, **kwargs):
        service_id = request.GET.get("service_id", None)
        if not service_id:
            return JsonResponse(
                {"message": "El ID del servicio es requerido."},
                status=HTTP_400_BAD_REQUEST,
            )
        service = Servicio.objects.filter(
            pk=service_id, estado=Servicio.EstadoChoices.ACTIVO, is_removed=False
        ).first()
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


class AvailableHoursAjax(BaseListViewAjax):
    model = Cita

    field_list = [
        "pk",
        "hora_agenda",
    ]
    ordering_fields = {
        "0": "hora_agenda",
    }

    def get_queryset(self):
        date_agenda_str = self.request.GET
        if date_agenda_str:
            print("\nDATE AGENDA SELECTED:", date_agenda_str, "\n")
        return super().get_queryset()


# endregion
"""========================================================================="""
