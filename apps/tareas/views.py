from typing import Optional

from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalReadView
from django import forms
from django.db.models import Count, Q, TextChoices
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

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
        "progreso_actual",
        "total_registros",
        "finalizado_en",
    ]

    ordering_fields = {
        "0": "nombre_proceso",
        "1": "estado",
        "2": "progreso_actual",
        "3": "progreso_actual",
        "4": "created",
        "5": "finalizado_en",
    }

    @staticmethod
    def _format_datetime(value) -> str:
        if not value:
            return "-- --"
        # created/finalizado_en se guardan en UTC (USE_TZ); se muestran en hora local
        return timezone.localtime(value).strftime("%d-%m-%Y %H:%M:%S")

    def _get_task_detail_url(self, task_id: int, status: str) -> Optional[str]:
        if status not in {self.model.Estado.FALLIDO}:
            return None
        return reverse_lazy("task_detail_modal", kwargs={"pk": task_id})

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            task_id: int = item["pk"]
            total = item.get("total_registros") or 0
            progreso = item.get("progreso_actual") or 0
            _status: str = item["estado"]
            item.update(
                {
                    "created_display": self._format_datetime(item.get("created")),
                    "finalizado_display": self._format_datetime(
                        item.get("finalizado_en")
                    ),
                    "estado_display": TareaEnProceso.Estado(_status).label,
                    "porcentaje": round(progreso * 100 / total) if total else 0,
                    "task_detail_url": self._get_task_detail_url(
                        task_id=task_id,
                        status=_status,
                    ),
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


class TaskDetailModalView(ProtectedView, BSModalReadView):
    template_name = "tareas/_task_detail_modal.html"
    model = TareaEnProceso
    context_object_name = "task"

    @staticmethod
    def _get_totals(result: dict) -> dict:
        return {
            "total_errors": result.get("total_errors", 0),
            "rows_error": result.get("rows_error", 0),
            "rows_ok": result.get("rows_ok", 0),
        }

    @staticmethod
    def _get_errors(result: dict) -> list:
        return result.get("errors", [])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task: TareaEnProceso = self.object
        metadata: dict = task.resultado_metadata or {}
        if not metadata:
            return context

        context.update(
            {
                "modal_url": reverse_lazy("task_detail_modal", kwargs={"pk": task.pk}),
                "estado_display": task.get_estado_display(),
                "created_display": TaskListView._format_datetime(task.created),
                "finalizado_display": TaskListView._format_datetime(task.finalizado_en),
                "porcentaje": task.porcentaje,
                "errors": self._get_errors(result=metadata),
                **self._get_totals(result=metadata),
            }
        )
        return context


# endregion
"""========================================================================="""
