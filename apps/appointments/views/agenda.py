from datetime import date, datetime

from django import forms
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from apps.appointments.models import Cita
from apps.appointments.views.handler import HandlerAgendaList
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomDateField
from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.utils.dates import format_full_date
from apps.common.views.base_views import ProtectedView

"""========================================================================="""
# region ........ Form


class AgendaFilterForm(forms.Form):
    status = forms.ChoiceField(
        label="Estado",
        required=False,
        initial=Cita.EstadoChoices.PENDIENTE,
        choices=Cita.EstadoChoices.choices,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    date_selected = CustomDateField(
        required=False,
        label="Fecha de la cita",
    )

    def clean(self):
        cleaned_data = super().clean()
        agendaStatus = cleaned_data.get("status", Cita.EstadoChoices.PENDIENTE)
        date_selected = cleaned_data.get("date_selected")

        filters = {"estado": agendaStatus}

        if date_selected:
            filters["fecha_agenda__in"] = [date_selected]
        return filters


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class AppointmentsView(ProtectedView, TemplateView):
    template_name = "appointments/list.html"

    @staticmethod
    def get_initial_month() -> str:
        today = timezone.localdate()
        return f"{today.strftime('%B %Y')}".capitalize()

    @staticmethod
    def get_date_instance(**kwargs) -> date:
        _date = kwargs.get("date", "")
        _today = timezone.localdate()
        date_instance = datetime.strptime(_date, "%Y-%m-%d").date() if _date else _today
        return date_instance

    def get_date_initial(self, **kwargs):
        _date = kwargs.get("date", "")
        if _date:
            date_instance = datetime.strptime(_date, "%Y-%m-%d").date()
            return date_instance.strftime("%d/%m/%Y")
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _date_selected = context["date"]
        date_instance = self.get_date_instance(date=_date_selected)
        date_initial = self.get_date_initial(date=_date_selected)
        context.update(
            {
                "filter_form": AgendaFilterForm(
                    initial={"date_selected": date_initial}
                ),
                "url_agenda_list": reverse_lazy("agenda_list"),
                "url_agenda_create": reverse_lazy(
                    "create_appointment_from_calendar", args=[_date_selected]
                ),
                "full_date": format_full_date(date_instance),
                "date_initial": date_initial,
                "cancel_url": reverse_lazy("calendar"),
            }
        )
        return context


class AgendaListView(BaseListViewAjax):
    model = Cita
    filter_form_class = AgendaFilterForm

    field_list = [
        "pk",
        "cliente__pk",
        "cliente_full_name",
        "cliente__telefono",
        "hora_agenda",
        "estado",
        "cantidad_servicios",
    ]

    ordering_fields = {
        "0": "hora_agenda",
        "1": "cliente_full_name",
        "3": "estado",
        "4": "cantidad_servicios",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cliente")
            .prefetch_related("detalles")
            .annotate(
                cantidad_servicios=Count("detalles"),
                cliente_full_name=Concat(
                    "cliente__nombre", Value(" "), "cliente__apellido"
                ),
            )
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["formatted_time"] = HandlerAgendaList.get_formatted_time(**value)
            value["agenda_see_modal_url"] = reverse_lazy(
                "agenda_see_modal", args=[value["pk"]]
            )
            value["whatsapp_modal_url"] = (
                reverse_lazy(
                    "client_whatsapp_modal", kwargs={"pk": value["cliente__pk"]}
                )
                if value["cliente__telefono"]
                else ""
            )
            value.update(HandlerAgendaList.get_options(value["pk"], value["estado"]))
        return values

    def additional_data(self, queryset):
        _filters = self.get_filters()
        date_selected = _filters.get("fecha_agenda__in", None)
        if not date_selected:
            return {}
        additional_data = self.model.objects.filter(
            fecha_agenda__in=date_selected
        ).aggregate(
            total_pendientes=Count("pk", filter=Q(estado=Cita.EstadoChoices.PENDIENTE)),
            total_completadas=Count(
                "pk", filter=Q(estado=Cita.EstadoChoices.COMPLETADA)
            ),
            total_canceladas=Count("pk", filter=Q(estado=Cita.EstadoChoices.CANCELADA)),
        )
        return {**additional_data}


# endregion
"""========================================================================="""
