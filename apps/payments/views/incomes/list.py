from datetime import timedelta

from django import forms
from django.db.models import Avg, Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomDateField
from apps.common.exports.columns import ExcelColumn
from apps.common.exports.excel_export_mixin import ExcelExportMixin
from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.utils.currency import format_currency
from apps.common.views.base_views import ProtectedView
from apps.payments.models import DetallePago

from ...choices import MetodoPago

DEFAULT_RANGE_IN_DAYS = 15
DATE_FORMAT = "%d/%m/%Y"
ALL_PAYMENT_METHODS = ""
PAYMENT_METHOD_CHOICES = [(ALL_PAYMENT_METHODS, "Todos"), *MetodoPago.CHOICES]
VALID_PAYMENT_METHODS = {value for value, _ in MetodoPago.CHOICES}

"""========================================================================="""
# region ........ Helpers


def get_default_date_range():
    today = timezone.localdate()
    return today - timedelta(days=DEFAULT_RANGE_IN_DAYS), today


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class IncomesFilterForm(forms.Form):
    date_from = CustomDateField(
        label="Desde",
        required=False,
    )
    date_to = CustomDateField(
        label="Hasta",
        required=False,
    )
    payment_method = forms.CharField(
        label="Método de pago",
        initial=ALL_PAYMENT_METHODS,
        required=False,
        widget=forms.Select(
            choices=PAYMENT_METHOD_CHOICES,
            attrs={"class": FORM_SELECT_CLASS},
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        default_from, default_to = get_default_date_range()
        date_from = cleaned_data.get("date_from") or default_from
        date_to = cleaned_data.get("date_to") or default_to
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        filters = {
            "fecha_pago__date__gte": date_from,
            "fecha_pago__date__lte": date_to,
        }
        payment_method = cleaned_data.get("payment_method")
        if payment_method in VALID_PAYMENT_METHODS:
            filters["metodo_pago"] = payment_method
        return filters


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class IncomesView(ProtectedView, TemplateView):
    template_name = "incomes/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_from, date_to = get_default_date_range()
        context.update(
            {
                "url_incomes_list": reverse_lazy("incomes_list"),
                "url_incomes_export": reverse_lazy("incomes_export"),
                "filter_form": IncomesFilterForm(
                    initial={
                        "date_from": date_from.strftime(DATE_FORMAT),
                        "date_to": date_to.strftime(DATE_FORMAT),
                    }
                ),
            }
        )
        return context


class IncomesListView(BaseListViewAjax):
    model = DetallePago
    include_options_column = False
    filter_form_class = IncomesFilterForm
    _filters = {"pago__is_removed": False}

    field_list = [
        "fecha_pago",
        "pago__cliente_nombre",
        "pago__fecha_cita",
        "metodo_pago",
        "referencia_pago",
        "monto_pago",
    ]

    ordering_fields = {
        "0": "fecha_pago",
        "1": "pago__cliente_nombre",
        "2": "pago__fecha_cita",
        "3": "metodo_pago",
        "4": "referencia_pago",
        "5": "monto_pago",
    }

    @staticmethod
    def _format_datetime(value) -> str:
        if not value:
            return "-- --"
        return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")

    def get_queryset(self):
        return super().get_queryset().select_related("pago")

    def get_values(self, queryset):
        values = super().get_values(queryset)
        payment_method_display = dict(MetodoPago.CHOICES)
        for item in values:
            item.update(
                {
                    "fecha_pago_display": self._format_datetime(item.get("fecha_pago")),
                    "fecha_cita_display": self._format_datetime(
                        item.get("pago__fecha_cita")
                    ),
                    "cliente_nombre": item.get("pago__cliente_nombre"),
                    "metodo_pago_display": payment_method_display.get(
                        item.get("metodo_pago"), item.get("metodo_pago")
                    ),
                    "referencia_pago_display": item.get("referencia_pago") or "—",
                    "monto_pago_formatted": format_currency(item.get("monto_pago")),
                }
            )
        return values

    def additional_data(self, queryset) -> dict:
        additional_data = queryset.aggregate(
            monto_total=Sum("monto_pago"),
            monto_promedio=Avg("monto_pago"),
        )
        return {
            "monto_total": format_currency(additional_data.get("monto_total")),
            "monto_promedio": format_currency(additional_data.get("monto_promedio")),
            "cantidad_ingresos": queryset.count(),
        }


class IncomesExportView(ExcelExportMixin, IncomesListView):
    force_export = True
    excel_filename = "ingresos"
    excel_sheet_title = "Ingresos"

    excel_columns = [
        ExcelColumn("Fecha pago", "fecha_pago_display", width=20, align="center"),
        ExcelColumn("Cliente", "cliente_nombre", width=30),
        ExcelColumn("Fecha cita", "fecha_cita_display", width=20, align="center"),
        ExcelColumn("Método de pago", "metodo_pago_display", width=18, align="center"),
        ExcelColumn("Referencia", "referencia_pago_display", width=22),
        ExcelColumn("Monto recibido", "monto_pago_formatted", width=16, align="right"),
    ]


# endregion
"""========================================================================="""
