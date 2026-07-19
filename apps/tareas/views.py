from django import forms
from django.db.models import Count, Q, TextChoices
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from bootstrap_modal_forms.forms import BSModalForm

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.views.base_views import ProtectedView
from apps.tareas.models import TareaEnProceso

"""========================================================================="""
# region ........ Form


class TasksFilterForm(BSModalForm):
    class StatusChoices(TextChoices):
        ALL = "all", "Todos"
        PENDIENTE = TareaEnProceso.Estado.PENDIENTE, "Pendientes"
        EN_PROCESO = TareaEnProceso.Estado.EN_PROCESO, "En proceso"
        COMPLETADO = TareaEnProceso.Estado.COMPLETADO, "Completados"
        FALLIDO = TareaEnProceso.Estado.FALLIDO, "Fallidos"

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        label="Estado",
        initial=StatusChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        cleaned_data = super().clean()
        is_data_valid = all(cleaned_data.values())
        if not is_data_valid:
            return {}

        data_to_filter = {}
        status = cleaned_data.get("status", self.StatusChoices.ALL)
        if status == self.StatusChoices.ALL:
            return data_to_filter
        data_to_filter["estado"] = status
        return data_to_filter


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class TaskView(ProtectedView, TemplateView):
    template_name = "tareas/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": TasksFilterForm(),
                "url_task_list": reverse_lazy("task_list"),
            }
        )
        return context


class TaskListView(BaseListViewAjax):
    model = TareaEnProceso
    include_options_column = False
    filter_form_class = TasksFilterForm

    field_list = [
        "pk",
        "created",
        "nombre_proceso",
        "estado",
        "modified",
        "progreso_actual",
        "total_registros",
        "finalizado_en",
    ]

    ordering_fields = {
        "0": "created",
        "1": "nombre_proceso",
        "2": "estado",
        "3": "modified",
        "4": "progreso_actual",
        "5": "progreso_actual",
        "6": "finalizado_en",
    }

    @staticmethod
    def _format_datetime(value) -> str:
        if not value:
            return "-- --"
        # created/modified se guardan en UTC (USE_TZ); se muestran en hora local
        return timezone.localtime(value).strftime("%d-%m-%Y %H:%M:%S")

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            total = item.get("total_registros") or 0
            progreso = item.get("progreso_actual") or 0
            item.update(
                {
                    "created_display": self._format_datetime(item.get("created")),
                    "modified_display": self._format_datetime(item.get("modified")),
                    "finalizado_display": self._format_datetime(
                        item.get("finalizado_en")
                    ),
                    "estado_display": TareaEnProceso.Estado(item["estado"]).label,
                    "porcentaje": round(progreso * 100 / total) if total else 0,
                }
            )
        return values

    @staticmethod
    def additional_data(queryset) -> dict:
        return TareaEnProceso.objects.aggregate(
            pending_totals=Count(
                "pk", filter=Q(estado=TareaEnProceso.Estado.PENDIENTE)
            ),
            process_totals=Count(
                "pk", filter=Q(estado=TareaEnProceso.Estado.EN_PROCESO)
            ),
            complete_totals=Count(
                "pk", filter=Q(estado=TareaEnProceso.Estado.COMPLETADO)
            ),
            failed_totals=Count("pk", filter=Q(estado=TareaEnProceso.Estado.FALLIDO)),
        )


# endregion
"""========================================================================="""
